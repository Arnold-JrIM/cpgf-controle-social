from __future__ import annotations

import operator
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Annotated, TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.types import Send

from cpgf.ai.contracts import ToolName
from cpgf.ai.evidence_contracts import (
    EvidenceBundle,
    EvidenceItem,
    EvidenceNeed,
    EvidencePlan,
    EvidenceSource,
)
from cpgf.ai.evidence_workers import (
    KnowledgeSearcher,
    WorkerOutcome,
    disabled_web_need,
    execute_data_need,
    retrieve_knowledge_need,
)
from cpgf.ai.web_evidence import WebSearcher, retrieve_web_need
from cpgf.dashboard.data import DashboardDataContext
from cpgf.knowledge.models import (
    AuthorityLevel,
    CorpusScope,
    SourceClass,
    TemporalStatus,
)

ORCHESTRATION_GRAPH_VERSION = "1.2.0"
_SIMULATION_WARNING = (
    "SIMULATION_ONLY: nenhuma fonte real foi consultada; os itens existem apenas para validar "
    "fan-out/fan-in, estado e contratos da arquitetura 2.0."
)
_SIMULATION_OBSERVED_AT = datetime(2000, 1, 1, tzinfo=timezone.utc)


class OrchestrationState(TypedDict, total=False):
    """Estado serializável do StateGraph governado da arquitetura 2.0."""

    plan: EvidencePlan
    current_need: EvidenceNeed
    worker_items: Annotated[list[EvidenceItem], operator.add]
    worker_warnings: Annotated[list[str], operator.add]
    dispatched_need_ids: tuple[str, ...]
    bundle: EvidenceBundle
    simulation_only: bool
    llm_called: bool


def _prepare_factory(*, simulation_mode: bool):
    def _prepare(state: OrchestrationState) -> dict[str, object]:
        plan = state["plan"]
        return {
            "worker_items": [],
            "worker_warnings": [],
            "dispatched_need_ids": tuple(need.need_id for need in plan.needs),
            "simulation_only": simulation_mode,
            "llm_called": False,
        }

    return _prepare


def _dispatch(state: OrchestrationState) -> str | list[Send]:
    plan = state["plan"]
    if not plan.needs:
        return "fan_in"
    return [
        Send(
            "evidence_worker",
            {
                "plan": plan,
                "current_need": need,
            },
        )
        for need in plan.needs
    ]


def _simulated_item(need: EvidenceNeed) -> EvidenceItem:
    common = {
        "evidence_id": f"ev-sim-{need.source.value}",
        "need_id": need.need_id,
        "source": need.source,
        "content": (
            "SIMULATED ONLY — evidência sintética criada exclusivamente para validar a "
            f"orquestração da necessidade {need.need_id}: {need.objective}"
        ),
        "citation": f"SIMULATED {need.source.value.upper()} EVIDENCE",
        "source_ref": f"simulated://{need.source.value}/{need.need_id}",
    }

    if need.source is EvidenceSource.DATA:
        return EvidenceItem(
            **common,
            tool=need.tool_hints[0] if need.tool_hints else ToolName.OVERVIEW,
            parameters=need.parameters,
            retrieval_method="tool",
        )

    if need.source is EvidenceSource.KNOWLEDGE:
        return EvidenceItem(
            **common,
            document_id="simulated-knowledge-document",
            source_class=need.source_classes[0] if need.source_classes else SourceClass.PROJECT,
            authority_level=AuthorityLevel.PROJECT_CONTROLLED,
            scope=need.scopes[0] if need.scopes else CorpusScope.CPGF_CORE,
            temporal_status=(
                need.temporal_statuses[0]
                if need.temporal_statuses
                else TemporalStatus.CONTEXTUAL
            ),
        )

    return EvidenceItem(
        **common,
        source_url="https://example.invalid/cpgf/simulated-evidence",
        observed_at=_SIMULATION_OBSERVED_AT,
        retrieval_method="web",
    )


def _worker_factory(
    *,
    data_context: DashboardDataContext | None,
    knowledge_retriever: KnowledgeSearcher | None,
    web_searcher: WebSearcher | None,
    web_clock: Callable[[], datetime] | None,
    simulation_mode: bool,
):
    def _worker(state: OrchestrationState) -> dict[str, object]:
        plan = state["plan"]
        need = state["current_need"]

        if simulation_mode:
            outcome = WorkerOutcome(items=(_simulated_item(need),))
        elif need.source is EvidenceSource.DATA:
            outcome = execute_data_need(plan=plan, need=need, context=data_context)
        elif need.source is EvidenceSource.KNOWLEDGE:
            outcome = retrieve_knowledge_need(
                plan=plan,
                need=need,
                retriever=knowledge_retriever,
            )
        elif web_searcher is None:
            outcome = disabled_web_need(need=need)
        else:
            outcome = retrieve_web_need(
                plan=plan,
                need=need,
                searcher=web_searcher,
                clock=web_clock,
            )

        return {
            "worker_items": list(outcome.items),
            "worker_warnings": list(outcome.warnings),
        }

    return _worker


def _fan_in(state: OrchestrationState) -> dict[str, object]:
    plan = state["plan"]
    order = {need.need_id: index for index, need in enumerate(plan.needs)}
    items = tuple(
        sorted(
            state.get("worker_items", []),
            key=lambda item: (order.get(item.need_id, 10_000), item.evidence_id),
        )
    )
    warnings = tuple(state.get("worker_warnings", []))
    if state.get("simulation_only", False):
        warnings = (_SIMULATION_WARNING, *warnings)
    bundle = EvidenceBundle(plan=plan, items=items, warnings=warnings)
    return {"bundle": bundle}


def build_evidence_orchestration_graph(
    *,
    data_context: DashboardDataContext | None = None,
    knowledge_retriever: KnowledgeSearcher | None = None,
    web_searcher: WebSearcher | None = None,
    web_clock: Callable[[], datetime] | None = None,
    simulation_mode: bool = False,
):
    """Compila o grafo 2.0; WEB só executa por adapter explicitamente injetado."""
    builder = StateGraph(OrchestrationState)
    builder.add_node("prepare", _prepare_factory(simulation_mode=simulation_mode))
    builder.add_node(
        "evidence_worker",
        _worker_factory(
            data_context=data_context,
            knowledge_retriever=knowledge_retriever,
            web_searcher=web_searcher,
            web_clock=web_clock,
            simulation_mode=simulation_mode,
        ),
    )
    builder.add_node("fan_in", _fan_in)

    builder.add_edge(START, "prepare")
    builder.add_conditional_edges("prepare", _dispatch, ["evidence_worker", "fan_in"])
    builder.add_edge("evidence_worker", "fan_in")
    builder.add_edge("fan_in", END)
    return builder.compile()


def run_evidence_orchestration(
    plan: EvidencePlan,
    *,
    data_context: DashboardDataContext | None = None,
    knowledge_retriever: KnowledgeSearcher | None = None,
    web_searcher: WebSearcher | None = None,
    web_clock: Callable[[], datetime] | None = None,
) -> EvidenceBundle:
    """Executa somente as fontes planejadas; WEB exige adapter explícito."""
    result = build_evidence_orchestration_graph(
        data_context=data_context,
        knowledge_retriever=knowledge_retriever,
        web_searcher=web_searcher,
        web_clock=web_clock,
    ).invoke({"plan": plan})
    return result["bundle"]


def run_simulated_orchestration(plan: EvidencePlan) -> EvidenceBundle:
    """Mantém o harness estrutural do PR #62 sem acessar fontes reais."""
    result = build_evidence_orchestration_graph(simulation_mode=True).invoke({"plan": plan})
    return result["bundle"]
