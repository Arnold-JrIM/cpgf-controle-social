from __future__ import annotations

import json
from types import SimpleNamespace

from cpgf.ai.contracts import ToolName
from cpgf.ai.evidence_contracts import EvidenceParameter, EvidenceSource
from cpgf.ai.semantic_orchestrator import (
    DataSelection,
    KnowledgeSelection,
    OpenAIResponsesOrchestratorProvider,
    OrchestratorCallMetadata,
    OrchestratorDecision,
    OrchestratorDecisionCall,
    PlanningStatus,
    WebSelection,
    plan_evidence,
)
from cpgf.knowledge.models import CorpusScope, SourceClass, TemporalStatus


def _metadata() -> OrchestratorCallMetadata:
    return OrchestratorCallMetadata(latency_ms=0.0)


class _StaticProvider:
    model = "gpt-4o-mini"

    def __init__(self, decision: OrchestratorDecision):
        self.decision = decision

    def decide(self, question: str) -> OrchestratorDecisionCall:
        return OrchestratorDecisionCall(output=self.decision, metadata=_metadata())


def test_plan_evidence_applies_normalization_to_custom_provider_decision():
    decision = OrchestratorDecision(
        reason="Combinar DATA, KNOWLEDGE e WEB.",
        clarification_question=None,
        data=DataSelection(
            selected=True,
            objective="Listar fornecedores recorrentes em 2025.",
            tool=ToolName.TOP_SUPPLIERS,
            parameters=(
                EvidenceParameter(name="year_start", value=2025),
                EvidenceParameter(name="year_end", value=2025),
                EvidenceParameter(name="limit", value=10),
            ),
        ),
        knowledge=KnowledgeSelection(
            selected=True,
            objective="Interpretar a atualização externa.",
            query_hint="contexto do CPGF",
            scopes=(CorpusScope.CPGF_CORE, CorpusScope.METHODOLOGY),
            temporal_statuses=(TemporalStatus.CURRENT, TemporalStatus.HISTORICAL),
            source_classes=(SourceClass.INSTITUTIONAL, SourceClass.NORMATIVE),
        ),
        web=WebSelection(
            selected=True,
            objective="Verificar mudança oficial na consulta pública.",
            query_hint="mudança oficial consulta pública CPGF",
            freshness_required=True,
            parameters=(
                EvidenceParameter(name="limit", value=10),
                EvidenceParameter(name="official_only", value=False),
            ),
        ),
    )

    question = (
        "Quais foram os 10 fornecedores mais recorrentes em 2025 e houve nos últimos 30 dias "
        "mudança oficial na consulta pública do CPGF?"
    )
    run = plan_evidence(question, provider=_StaticProvider(decision))

    assert run.status is PlanningStatus.PLANNED
    assert run.plan is not None
    assert run.plan.requested_sources == (EvidenceSource.DATA, EvidenceSource.WEB)
    assert "DROPPED_KNOWLEDGE_WITHOUT_GOVERNED_INTENT" in run.normalization_notes
    web = run.plan.need_for(EvidenceSource.WEB)
    assert {parameter.name: parameter.value for parameter in web.parameters} == {
        "limit": 5,
        "max_age_days": 30,
        "official_only": True,
    }


class _Responses:
    def __init__(self, output: dict[str, object]):
        self.output = output

    def create(self, **kwargs):
        return SimpleNamespace(
            id="resp-normalized",
            model="gpt-4o-mini",
            output_text=json.dumps(self.output),
            usage=SimpleNamespace(input_tokens=10, output_tokens=10),
        )


class _Client:
    def __init__(self, output: dict[str, object]):
        self.responses = _Responses(output)


def test_provider_sanitizes_residual_fields_on_unselected_source():
    output = {
        "reason": "A pergunta exige somente WEB.",
        "clarification_question": None,
        "data": {
            "selected": False,
            "objective": None,
            "tool": None,
            "parameters": [],
        },
        "knowledge": {
            "selected": False,
            "objective": "Campo residual que antes causava ValidationError.",
            "query_hint": "resíduo",
            "scopes": ["cpgf_core"],
            "temporal_statuses": ["current"],
            "source_classes": ["normative"],
            "parameters": [{"name": "limit", "value": 5}],
        },
        "web": {
            "selected": True,
            "objective": "Consultar publicação oficial recente.",
            "query_hint": "publicação oficial CPGF",
            "freshness_required": True,
            "parameters": [],
        },
    }
    provider = OpenAIResponsesOrchestratorProvider(client=_Client(output))

    call = provider.decide(
        "Qual publicação oficial dos últimos 60 dias menciona o CPGF?"
    )

    assert call.output.selected_sources == (EvidenceSource.WEB,)
    assert call.output.knowledge == KnowledgeSelection(selected=False)
    assert "NORMALIZED_UNSELECTED_KNOWLEDGE" in call.normalization_notes
    assert {parameter.name: parameter.value for parameter in call.output.web.parameters} == {
        "limit": 5,
        "max_age_days": 60,
        "official_only": True,
    }


def test_provider_clarification_clears_selected_sources_instead_of_failing_schema_contract():
    output = {
        "reason": "Falta período obrigatório para a ferramenta DATA.",
        "clarification_question": "Qual período você deseja analisar?",
        "data": {
            "selected": True,
            "objective": "Consultar visão geral.",
            "tool": "overview",
            "parameters": [],
        },
        "knowledge": {
            "selected": False,
            "objective": None,
            "query_hint": None,
            "scopes": [],
            "temporal_statuses": [],
            "source_classes": [],
            "parameters": [],
        },
        "web": {
            "selected": False,
            "objective": None,
            "query_hint": None,
            "freshness_required": False,
            "parameters": [],
        },
    }
    provider = OpenAIResponsesOrchestratorProvider(client=_Client(output))

    run = plan_evidence("Mostre o panorama geral dos gastos.", provider=provider)

    assert run.status is PlanningStatus.CLARIFICATION_REQUIRED
    assert run.plan is None
    assert run.clarification_question == "Qual período você deseja analisar?"
    assert "CLARIFICATION_FAIL_CLOSED" in run.normalization_notes
