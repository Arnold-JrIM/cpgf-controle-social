from __future__ import annotations

from cpgf.ai.contracts import ToolName
from cpgf.ai.evidence_contracts import EvidenceNeed, EvidencePlan, EvidenceSource
from cpgf.ai.model_policy import (
    DEFAULT_LLM_MODEL,
    LLM_MODEL_POLICY_VERSION,
    project_llm_model,
)
from cpgf.ai.orchestration_graph import (
    ORCHESTRATION_GRAPH_VERSION,
    build_evidence_orchestration_graph,
    run_simulated_orchestration,
)
from cpgf.knowledge.models import CorpusScope, SourceClass, TemporalStatus


def _three_source_plan() -> EvidencePlan:
    return EvidencePlan(
        question="Compare dados, norma e informação externa atual sobre o CPGF.",
        reason="Teste estrutural multi-source.",
        needs=(
            EvidenceNeed(
                need_id="need-data",
                source=EvidenceSource.DATA,
                objective="Consultar agregações governadas do Serving.",
                tool_hints=(ToolName.TOP_UGS,),
            ),
            EvidenceNeed(
                need_id="need-knowledge",
                source=EvidenceSource.KNOWLEDGE,
                objective="Recuperar enquadramento documental governado.",
                scopes=(CorpusScope.CPGF_CORE,),
                temporal_statuses=(TemporalStatus.CURRENT,),
                source_classes=(SourceClass.NORMATIVE,),
            ),
            EvidenceNeed(
                need_id="need-web",
                source=EvidenceSource.WEB,
                objective="Consultar informação externa que exija freshness.",
                freshness_required=True,
            ),
        ),
    )


def test_project_model_policy_is_gpt_4o_mini():
    assert DEFAULT_LLM_MODEL == "gpt-4o-mini"
    assert project_llm_model() == "gpt-4o-mini"
    assert LLM_MODEL_POLICY_VERSION == "1.0.0"


def test_orchestration_graph_versions():
    assert ORCHESTRATION_GRAPH_VERSION == "1.0.0"


def test_three_source_plan_fans_out_and_fans_in_to_complete_bundle():
    plan = _three_source_plan()
    graph = build_evidence_orchestration_graph()
    result = graph.invoke({"plan": plan})

    assert result["dispatched_need_ids"] == (
        "need-data",
        "need-knowledge",
        "need-web",
    )
    assert result["simulation_only"] is True
    assert result["llm_called"] is False

    bundle = result["bundle"]
    assert bundle.is_complete is True
    assert bundle.missing_required_need_ids == ()
    assert tuple(item.need_id for item in bundle.items) == result["dispatched_need_ids"]
    assert tuple(item.source for item in bundle.items) == (
        EvidenceSource.DATA,
        EvidenceSource.KNOWLEDGE,
        EvidenceSource.WEB,
    )
    assert all(item.content.startswith("SIMULATED ONLY") for item in bundle.items)
    assert bundle.warnings and bundle.warnings[0].startswith("SIMULATION_ONLY")


def test_worker_provenance_respects_each_source_contract():
    bundle = run_simulated_orchestration(_three_source_plan())
    data, knowledge, web = bundle.items

    assert data.tool is ToolName.TOP_UGS
    assert data.retrieval_method == "tool"
    assert data.document_id is None
    assert data.source_url is None

    assert knowledge.tool is None
    assert knowledge.document_id == "simulated-knowledge-document"
    assert knowledge.scope is CorpusScope.CPGF_CORE
    assert knowledge.temporal_status is TemporalStatus.CURRENT
    assert knowledge.source_class is SourceClass.NORMATIVE

    assert web.tool is None
    assert web.source_url == "https://example.invalid/cpgf/simulated-evidence"
    assert web.observed_at is not None
    assert web.retrieval_method == "web"


def test_zero_need_plan_skips_workers_and_builds_empty_complete_bundle():
    plan = EvidencePlan(
        question="Pergunta que não exige fonte externa neste teste.",
        reason="Valida caminho sem fan-out.",
        needs=(),
    )
    result = build_evidence_orchestration_graph().invoke({"plan": plan})

    assert result["dispatched_need_ids"] == ()
    assert result["worker_items"] == []
    assert result["bundle"].items == ()
    assert result["bundle"].is_complete is True


def test_single_source_plan_only_dispatches_planned_need():
    plan = EvidencePlan(
        question="Quais dados agregados do CPGF devem ser consultados?",
        reason="Valida fan-out unitário.",
        needs=(
            EvidenceNeed(
                need_id="need-data-only",
                source=EvidenceSource.DATA,
                objective="Usar somente o Serving governado.",
                tool_hints=(ToolName.OVERVIEW,),
            ),
        ),
    )
    result = build_evidence_orchestration_graph().invoke({"plan": plan})

    assert result["dispatched_need_ids"] == ("need-data-only",)
    assert len(result["bundle"].items) == 1
    assert result["bundle"].items[0].source is EvidenceSource.DATA


def test_simulated_bundle_serialization_is_stable_and_explicit():
    bundle = run_simulated_orchestration(_three_source_plan())
    payload = bundle.model_dump(mode="json")

    assert payload["contract_version"] == "1.0.0"
    assert payload["plan"]["question"].startswith("Compare dados")
    assert [item["source"] for item in payload["items"]] == ["data", "knowledge", "web"]
    assert payload["warnings"][0].startswith("SIMULATION_ONLY")
