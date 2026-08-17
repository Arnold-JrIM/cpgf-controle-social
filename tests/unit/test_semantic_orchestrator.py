from __future__ import annotations

import json
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from cpgf.ai.contracts import ToolName
from cpgf.ai.evidence_contracts import EvidenceParameter, EvidenceSource
from cpgf.ai.semantic_orchestrator import (
    SEMANTIC_ORCHESTRATOR_POLICY_VERSION,
    SEMANTIC_ORCHESTRATOR_VERSION,
    DataSelection,
    EvidencePlanningRun,
    KnowledgeSelection,
    OpenAIResponsesOrchestratorProvider,
    OrchestratorCallMetadata,
    OrchestratorDecision,
    OrchestratorDecisionCall,
    PlanningStatus,
    WebSelection,
    build_evidence_plan,
    plan_evidence,
)
from cpgf.knowledge.models import CorpusScope, SourceClass, TemporalStatus


def _metadata() -> OrchestratorCallMetadata:
    return OrchestratorCallMetadata(latency_ms=0.0)


def _data_off() -> DataSelection:
    return DataSelection(selected=False)


def _knowledge_off() -> KnowledgeSelection:
    return KnowledgeSelection(selected=False)


def _web_off() -> WebSelection:
    return WebSelection(selected=False)


def _decision(
    *,
    data: DataSelection | None = None,
    knowledge: KnowledgeSelection | None = None,
    web: WebSelection | None = None,
    clarification_question: str | None = None,
) -> OrchestratorDecision:
    return OrchestratorDecision(
        reason="Plano mínimo de evidências para o teste.",
        clarification_question=clarification_question,
        data=data or _data_off(),
        knowledge=knowledge or _knowledge_off(),
        web=web or _web_off(),
    )


class _StaticProvider:
    model = "gpt-4o-mini"

    def __init__(self, decision: OrchestratorDecision):
        self.decision = decision
        self.calls: list[str] = []

    def decide(self, question: str) -> OrchestratorDecisionCall:
        self.calls.append(question)
        return OrchestratorDecisionCall(output=self.decision, metadata=_metadata())


class _FailingProvider:
    model = "gpt-4o-mini"

    def decide(self, question: str) -> OrchestratorDecisionCall:
        raise RuntimeError("provider indisponível")


def test_orchestrator_versions_and_governed_model():
    assert SEMANTIC_ORCHESTRATOR_VERSION == "1.1.0"
    assert SEMANTIC_ORCHESTRATOR_POLICY_VERSION == "1.1.0"
    provider = OpenAIResponsesOrchestratorProvider(client=object())
    assert provider.model == "gpt-4o-mini"


def test_data_plan_is_executable_and_parameters_are_canonicalized():
    decision = _decision(
        data=DataSelection(
            selected=True,
            objective="Listar as UGs priorizadas em 2025.",
            tool=ToolName.TOP_UGS,
            parameters=(
                EvidenceParameter(name="year_start", value=2025),
                EvidenceParameter(name="year_end", value=2025),
            ),
        )
    )

    plan = build_evidence_plan("Quais UGs foram priorizadas em 2025?", decision)

    assert plan.requested_sources == (EvidenceSource.DATA,)
    need = plan.needs[0]
    assert need.need_id == "need-data"
    assert need.tool_hints == (ToolName.TOP_UGS,)
    assert {parameter.name: parameter.value for parameter in need.parameters} == {
        "limit": 20,
        "ug_codes": (),
        "year_end": 2025,
        "year_start": 2025,
    }


def test_three_source_decision_builds_canonical_multilabel_plan():
    decision = _decision(
        data=DataSelection(
            selected=True,
            objective="Quantificar UGs priorizadas em 2025.",
            tool=ToolName.TOP_UGS,
            parameters=(
                EvidenceParameter(name="year_start", value=2025),
                EvidenceParameter(name="year_end", value=2025),
                EvidenceParameter(name="limit", value=10),
            ),
        ),
        knowledge=KnowledgeSelection(
            selected=True,
            objective="Recuperar o enquadramento normativo aplicável.",
            query_hint="normas vigentes do CPGF e suprimento de fundos",
            scopes=(CorpusScope.CPGF_CORE,),
            temporal_statuses=(TemporalStatus.CURRENT,),
            source_classes=(SourceClass.NORMATIVE,),
            parameters=(EvidenceParameter(name="limit", value=4),),
        ),
        web=WebSelection(
            selected=True,
            objective="Verificar atualização oficial externa recente.",
            query_hint="CPGF atualização oficial 2026",
            freshness_required=True,
            parameters=(
                EvidenceParameter(name="official_only", value=True),
                EvidenceParameter(name="max_age_days", value=60),
            ),
        ),
    )

    plan = build_evidence_plan(
        "Compare os dados de 2025, a norma vigente e atualizações oficiais recentes do CPGF.",
        decision,
    )

    assert decision.selected_sources == (
        EvidenceSource.DATA,
        EvidenceSource.KNOWLEDGE,
        EvidenceSource.WEB,
    )
    assert plan.requested_sources == decision.selected_sources
    assert tuple(need.need_id for need in plan.needs) == (
        "need-data",
        "need-knowledge",
        "need-web",
    )
    assert plan.need_for(EvidenceSource.KNOWLEDGE).scopes == (CorpusScope.CPGF_CORE,)
    web_parameters = {
        parameter.name: parameter.value
        for parameter in plan.need_for(EvidenceSource.WEB).parameters
    }
    assert web_parameters == {
        "limit": 5,
        "max_age_days": 60,
        "official_only": True,
    }


def test_missing_required_data_argument_fails_closed_in_planning():
    decision = _decision(
        data=DataSelection(
            selected=True,
            objective="Consultar visão geral sem inventar período.",
            tool=ToolName.OVERVIEW,
            parameters=(),
        )
    )
    provider = _StaticProvider(decision)

    run = plan_evidence("Mostre a visão geral dos gastos.", provider=provider)

    assert run.status is PlanningStatus.FAILED
    assert run.plan is None
    assert run.warning == "ORCHESTRATOR_PLAN_INVALID:ValidationError"


def test_data_selection_rejects_methodology_tool():
    with pytest.raises(ValidationError):
        DataSelection(
            selected=True,
            objective="Não tratar metodologia como fato do Serving.",
            tool=ToolName.METHODOLOGY,
        )


def test_knowledge_selection_requires_explicit_scope_and_temporality():
    with pytest.raises(ValidationError):
        KnowledgeSelection(
            selected=True,
            objective="Buscar norma.",
            query_hint="norma CPGF",
        )


def test_web_selection_requires_freshness():
    with pytest.raises(ValidationError):
        WebSelection(
            selected=True,
            objective="Buscar fonte externa atual.",
            query_hint="CPGF fonte oficial",
            freshness_required=False,
        )


def test_clarification_prevents_any_source_dispatch():
    decision = _decision(clarification_question="Qual período você deseja analisar?")
    provider = _StaticProvider(decision)

    run = plan_evidence("Quais UGs tiveram mais alertas?", provider=provider)

    assert run.status is PlanningStatus.CLARIFICATION_REQUIRED
    assert run.plan is None
    assert run.clarification_question == "Qual período você deseja analisar?"
    assert provider.calls == ["Quais UGs tiveram mais alertas?"]


def test_provider_failure_is_fail_closed():
    run = plan_evidence("Quais normas regem o CPGF?", provider=_FailingProvider())

    assert run.status is PlanningStatus.FAILED
    assert run.plan is None
    assert run.warning == "ORCHESTRATOR_PROVIDER_FAILED:RuntimeError"


def test_empty_source_set_is_explicitly_plannable_without_fake_evidence():
    provider = _StaticProvider(_decision())

    run = plan_evidence("Olá, como você funciona?", provider=provider)

    assert isinstance(run, EvidencePlanningRun)
    assert run.status is PlanningStatus.PLANNED
    assert run.plan is not None
    assert run.plan.needs == ()
    assert run.plan.requested_sources == ()


class _RecordingResponses:
    def __init__(self, output: dict[str, object]):
        self.output = output
        self.kwargs: dict[str, object] | None = None

    def create(self, **kwargs):
        self.kwargs = kwargs
        return SimpleNamespace(
            id="resp-orchestrator",
            model="gpt-4o-mini",
            output_text=json.dumps(self.output),
            usage=SimpleNamespace(input_tokens=100, output_tokens=25),
        )


class _RecordingClient:
    def __init__(self, output: dict[str, object]):
        self.responses = _RecordingResponses(output)


def test_openai_provider_uses_strict_schema_store_false_and_only_gpt_4o_mini():
    output = {
        "reason": "A pergunta exige apenas documentação normativa governada.",
        "clarification_question": None,
        "data": {
            "selected": False,
            "objective": None,
            "tool": None,
            "parameters": [],
        },
        "knowledge": {
            "selected": True,
            "objective": "Recuperar normas vigentes do CPGF.",
            "query_hint": "normas vigentes CPGF suprimento de fundos",
            "scopes": ["cpgf_core"],
            "temporal_statuses": ["current"],
            "source_classes": ["normative"],
            "parameters": [{"name": "limit", "value": 5}],
        },
        "web": {
            "selected": False,
            "objective": None,
            "query_hint": None,
            "freshness_required": False,
            "parameters": [],
        },
    }
    client = _RecordingClient(output)
    provider = OpenAIResponsesOrchestratorProvider(client=client)

    call = provider.decide("Quais normas vigentes regem o CPGF?")

    assert call.output.selected_sources == (EvidenceSource.KNOWLEDGE,)
    kwargs = client.responses.kwargs
    assert kwargs is not None
    assert kwargs["model"] == "gpt-4o-mini"
    assert kwargs["store"] is False
    assert kwargs["text"]["format"]["type"] == "json_schema"
    assert kwargs["text"]["format"]["strict"] is True
    payload = json.loads(kwargs["input"])
    assert payload["question"] == "Quais normas vigentes regem o CPGF?"
    assert {tool["name"] for tool in payload["capabilities"]["data_tools"]} == {
        "overview",
        "trail_prevalence",
        "top_ugs",
        "top_suppliers",
        "territorial_metric",
        "territorial_ug_context",
    }
