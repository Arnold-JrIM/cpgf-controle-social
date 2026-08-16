from __future__ import annotations

from cpgf.ai.retrieval_planner import PlannedKnowledgeRetriever, plan_knowledge_retrieval
from cpgf.knowledge.models import CorpusScope, TemporalStatus


def test_planner_routes_general_cpgf_normative_question_to_current_core() -> None:
    plan = plan_knowledge_retrieval(
        "Qual é a base legal do regime de adiantamento que fundamenta o suprimento de fundos?"
    )

    assert plan.scopes == (CorpusScope.CPGF_CORE,)
    assert plan.temporal_statuses == (TemporalStatus.CURRENT,)
    assert plan.deterministic is True


def test_planner_routes_benford_to_contextual_methodology() -> None:
    plan = plan_knowledge_retrieval(
        "Qual referência metodológica explica os fundamentos da Lei de Benford para auditoria?"
    )

    assert plan.scopes == (CorpusScope.METHODOLOGY,)
    assert plan.temporal_statuses == (TemporalStatus.CONTEXTUAL,)
    assert plan.trail_hints == ("T08",)


def test_planner_combines_portal_transparency_and_control_social_scopes() -> None:
    plan = plan_knowledge_retrieval(
        "Que estudos discutem o Portal da Transparência e o CPGF sob a ótica do controle social?"
    )

    assert plan.scopes == (CorpusScope.CPGF_CORE, CorpusScope.METHODOLOGY)
    assert plan.temporal_statuses == (TemporalStatus.CONTEXTUAL,)


def test_planner_routes_tcu_question_to_control_external() -> None:
    plan = plan_knowledge_retrieval(
        "Qual decisão do TCU trata de fiscalização contínua dos gastos com CPGF?"
    )

    assert plan.scopes == (CorpusScope.CONTROL_EXTERNAL,)
    assert plan.temporal_statuses == (TemporalStatus.CONTEXTUAL,)


def test_planner_marks_fragmentation_as_current_and_contextual() -> None:
    plan = plan_knowledge_retrieval(
        "Que fontes ajudam a avaliar possível fracionamento quando há despesas repetidas?"
    )

    assert plan.scopes == (CorpusScope.CPGF_CORE,)
    assert plan.temporal_statuses == (TemporalStatus.CURRENT, TemporalStatus.CONTEXTUAL)
    assert plan.trail_hints == ("T03", "T04", "T05")


class _RecordingRetriever:
    def __init__(self) -> None:
        self.filters: dict[str, object] | None = None

    def search(self, query: str, *, limit: int = 5, **filters: object) -> list[object]:
        self.filters = {"query": query, "limit": limit, **filters}
        return []


def test_planned_retriever_applies_runtime_filters() -> None:
    base = _RecordingRetriever()
    retriever = PlannedKnowledgeRetriever(base)

    retriever.search("Qual decisão do TCU trata de fiscalização contínua do CPGF?", limit=7)

    assert base.filters == {
        "query": "Qual decisão do TCU trata de fiscalização contínua do CPGF?",
        "limit": 7,
        "scopes": {"control_external"},
        "temporal_statuses": {"contextual"},
    }
