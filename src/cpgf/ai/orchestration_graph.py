from __future__ import annotations

import operator
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
from cpgf.knowledge.models import (
    AuthorityLevel,
    CorpusScope,
    SourceClass,
    TemporalStatus,
)

ORCHESTRATION_GRAPH_VERSION = "1.0.0"
_SIMULATION_WARNING = (
    "SIMULATION_ONLY: nenhuma fonte real foi consultada; os itens existem apenas para validar "
    "fan-out/fan-in, estado e contratos da arquitetura 2.0."
)
_SIMULATION_OBSERVED_AT = datetime(2000, 1, 1, tzinfo=timezone.utc)


class OrchestrationState(TypedDict, total=False):
    """Estado mínimo do primeiro StateGraph governado da arquitetura 2.0."""

    plan: EvidencePlan
    current_need: EvidenceNeed
    worker_items: Annotated[list[EvidenceItem], operator.add]
    dispatched_need_ids: tuple[str, ...]
    bundle: EvidenceBundle
    simulation_only: bool
    llm_called: bool


def _prepare(state: OrchestrationState) -> dict[str, object]:
    plan = state["plan"]
    return {
        "worker_items": [],
        "dispatched_need_ids": tuple(need.need_id for need in plan.needs),
        "simulation_only": True,
        "llm_called": False,
    }


def _dispatch(state: OrchestrationState) -> str | list[Send]:
    plan = state["plan"]
    if not plan.needs:
        return "fan_in"
    return [
        Send(
            "simulated_worker",
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


def _simulated_worker(state: OrchestrationState) -> dict[str, object]:
    return {"worker_items": [_simulated_item(state["current_need"])]}


def _fan_in(state: OrchestrationState) -> dict[str, object]:
    plan = state["plan"]
    order = {need.need_id: index for index, need in enumerate(plan.needs)}
    items = tuple(
        sorted(
            state.get("worker_items", []),
            key=lambda item: (order.get(item.need_id, 10_000), item.evidence_id),
        )
    )
    bundle = EvidenceBundle(plan=plan, items=items, warnings=(_SIMULATION_WARNING,))
    return {"bundle": bundle}


def build_evidence_orchestration_graph():
    """Compila o primeiro grafo 2.0; workers são deliberadamente simulados."""
    builder = StateGraph(OrchestrationState)
    builder.add_node("prepare", _prepare)
    builder.add_node("simulated_worker", _simulated_worker)
    builder.add_node("fan_in", _fan_in)

    builder.add_edge(START, "prepare")
    builder.add_conditional_edges("prepare", _dispatch, ["simulated_worker", "fan_in"])
    builder.add_edge("simulated_worker", "fan_in")
    builder.add_edge("fan_in", END)
    return builder.compile()


def run_simulated_orchestration(plan: EvidencePlan) -> EvidenceBundle:
    """Executa somente a simulação estrutural e devolve o EvidenceBundle validado."""
    result = build_evidence_orchestration_graph().invoke({"plan": plan})
    return result["bundle"]
