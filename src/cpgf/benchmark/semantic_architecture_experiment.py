from __future__ import annotations

from collections import Counter, defaultdict
from enum import StrEnum
from statistics import mean

from pydantic import BaseModel, ConfigDict

from cpgf.ai.retrieval_planner import plan_knowledge_retrieval
from cpgf.ai.router import RouteDecision, route_question
from cpgf.ai.semantic_experiment import SemanticProvider

from .joint_retrieval_v4 import JointRetrievalHoldoutV4Case, JointRetrievalHoldoutV4Suite


class SemanticArchitecture(StrEnum):
    DETERMINISTIC = "A_deterministic"
    LLM_ROUTE = "B_llm_route"
    HYBRID_ADJUDICATED = "C_hybrid_adjudicated"


class ArchitecturePrediction(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    route: str
    scopes: tuple[str, ...]
    temporal_statuses: tuple[str, ...]
    llm_called: bool
    schema_valid: bool = True
    response_id: str | None = None
    response_model: str | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    latency_ms: float | None = None
    error: str | None = None

    @property
    def signature(self) -> tuple[str, tuple[str, ...], tuple[str, ...]]:
        return (
            self.route,
            tuple(sorted(self.scopes)),
            tuple(sorted(self.temporal_statuses)),
        )


def _deterministic_prediction(question: str) -> ArchitecturePrediction:
    decision = route_question(question)
    plan = plan_knowledge_retrieval(question, decision=decision)
    return ArchitecturePrediction(
        route=decision.route.value,
        scopes=tuple(scope.value for scope in plan.scopes),
        temporal_statuses=tuple(status.value for status in plan.temporal_statuses),
        llm_called=False,
    )


def _llm_route_prediction(question: str, provider: SemanticProvider) -> ArchitecturePrediction:
    call = provider.classify_route(question)
    decision = RouteDecision(
        route=call.output.route,
        reason=call.output.reason,
        deterministic=False,
    )
    plan = plan_knowledge_retrieval(question, decision=decision)
    metadata = call.metadata
    return ArchitecturePrediction(
        route=call.output.route.value,
        scopes=tuple(scope.value for scope in plan.scopes),
        temporal_statuses=tuple(status.value for status in plan.temporal_statuses),
        llm_called=True,
        response_id=metadata.response_id,
        response_model=metadata.response_model,
        input_tokens=metadata.input_tokens,
        output_tokens=metadata.output_tokens,
        latency_ms=metadata.latency_ms,
    )


def _hybrid_prediction(question: str, provider: SemanticProvider) -> ArchitecturePrediction:
    deterministic = route_question(question)
    call = provider.adjudicate_plan(
        question,
        deterministic_decision=deterministic,
    )
    metadata = call.metadata
    return ArchitecturePrediction(
        route=call.output.route.value,
        scopes=tuple(scope.value for scope in call.output.scopes),
        temporal_statuses=tuple(status.value for status in call.output.temporal_statuses),
        llm_called=True,
        response_id=metadata.response_id,
        response_model=metadata.response_model,
        input_tokens=metadata.input_tokens,
        output_tokens=metadata.output_tokens,
        latency_ms=metadata.latency_ms,
    )


def _failed_prediction(exc: Exception, *, llm_called: bool) -> ArchitecturePrediction:
    return ArchitecturePrediction(
        route="__invalid__",
        scopes=(),
        temporal_statuses=(),
        llm_called=llm_called,
        schema_valid=False,
        error=f"{type(exc).__name__}: {exc}",
    )


def _exactness(
    case: JointRetrievalHoldoutV4Case,
    prediction: ArchitecturePrediction,
) -> dict[str, bool]:
    expected_scopes = {scope.value for scope in case.expected_scopes}
    expected_temporal = {status.value for status in case.expected_temporal_statuses}
    scope_exact = expected_scopes == set(prediction.scopes)
    temporal_exact = expected_temporal == set(prediction.temporal_statuses)
    route_exact = case.expected_route.value == prediction.route
    return {
        "route_exact": route_exact,
        "scope_exact": scope_exact,
        "temporal_exact": temporal_exact,
        "filter_joint_exact": scope_exact and temporal_exact,
        "joint_exact": route_exact and scope_exact and temporal_exact,
    }


def _run_prediction(
    architecture: SemanticArchitecture,
    question: str,
    provider: SemanticProvider | None,
) -> ArchitecturePrediction:
    if architecture == SemanticArchitecture.DETERMINISTIC:
        return _deterministic_prediction(question)
    if provider is None:
        raise ValueError("arquitetura com LLM exige SemanticProvider")
    try:
        if architecture == SemanticArchitecture.LLM_ROUTE:
            return _llm_route_prediction(question, provider)
        return _hybrid_prediction(question, provider)
    except Exception as exc:  # a falha precisa permanecer na evidência experimental
        return _failed_prediction(exc, llm_called=True)


def _repetition_summary(rows: list[dict[str, object]]) -> dict[str, object]:
    cases = len(rows)
    metrics = (
        "route_exact",
        "scope_exact",
        "temporal_exact",
        "filter_joint_exact",
        "joint_exact",
    )
    summary: dict[str, object] = {"cases": cases}
    for metric in metrics:
        count = sum(bool(row[metric]) for row in rows)
        summary[metric] = count
        summary[f"{metric}_rate"] = count / cases if cases else 0.0
    invalid = sum(not bool(row["schema_valid"]) for row in rows)
    summary["schema_violations"] = invalid
    summary["schema_violation_rate"] = invalid / cases if cases else 0.0
    summary["llm_calls"] = sum(bool(row["llm_called"]) for row in rows)
    latencies = [float(row["latency_ms"]) for row in rows if row["latency_ms"] is not None]
    summary["mean_latency_ms"] = mean(latencies) if latencies else 0.0
    summary["input_tokens"] = sum(int(row["input_tokens"] or 0) for row in rows)
    summary["output_tokens"] = sum(int(row["output_tokens"] or 0) for row in rows)
    return summary


def evaluate_semantic_architectures(
    suite: JointRetrievalHoldoutV4Suite,
    *,
    provider: SemanticProvider | None,
    repeats: int = 3,
) -> dict[str, object]:
    if repeats < 1 or repeats > 10:
        raise ValueError("repeats deve estar entre 1 e 10")

    architecture_rows: dict[str, list[dict[str, object]]] = defaultdict(list)
    repetition_summaries: dict[str, list[dict[str, object]]] = defaultdict(list)

    for architecture in SemanticArchitecture:
        effective_repeats = 1 if architecture == SemanticArchitecture.DETERMINISTIC else repeats
        for repeat in range(1, effective_repeats + 1):
            rows: list[dict[str, object]] = []
            for case in suite.cases:
                prediction = _run_prediction(architecture, case.question, provider)
                exact = _exactness(case, prediction)
                row = {
                    "architecture": architecture.value,
                    "repeat": repeat,
                    "id": case.id,
                    "category": case.category.value,
                    "expected_route": case.expected_route.value,
                    "expected_scopes": sorted(scope.value for scope in case.expected_scopes),
                    "expected_temporal_statuses": sorted(
                        status.value for status in case.expected_temporal_statuses
                    ),
                    "predicted_route": prediction.route,
                    "predicted_scopes": sorted(prediction.scopes),
                    "predicted_temporal_statuses": sorted(prediction.temporal_statuses),
                    "schema_valid": prediction.schema_valid,
                    "llm_called": prediction.llm_called,
                    "response_id": prediction.response_id,
                    "response_model": prediction.response_model,
                    "input_tokens": prediction.input_tokens,
                    "output_tokens": prediction.output_tokens,
                    "latency_ms": prediction.latency_ms,
                    "error": prediction.error,
                    **exact,
                }
                rows.append(row)
                architecture_rows[architecture.value].append(row)
            repetition_summaries[architecture.value].append(_repetition_summary(rows))

    stability: dict[str, dict[str, object]] = {}
    for architecture in (
        SemanticArchitecture.LLM_ROUTE,
        SemanticArchitecture.HYBRID_ADJUDICATED,
    ):
        signatures: defaultdict[
            str, list[tuple[str, tuple[str, ...], tuple[str, ...]]]
        ] = defaultdict(list)
        for row in architecture_rows[architecture.value]:
            signature = (
                str(row["predicted_route"]),
                tuple(row["predicted_scopes"]),
                tuple(row["predicted_temporal_statuses"]),
            )
            signatures[str(row["id"])].append(signature)
        modal_shares: list[float] = []
        identical = 0
        for values in signatures.values():
            most_common = Counter(values).most_common(1)[0][1]
            share = most_common / len(values)
            modal_shares.append(share)
            if most_common == len(values):
                identical += 1
        stability[architecture.value] = {
            "mean_modal_share": mean(modal_shares) if modal_shares else 0.0,
            "all_repetitions_identical_cases": identical,
            "cases": len(signatures),
        }

    aggregate: dict[str, dict[str, object]] = {}
    for architecture, summaries in repetition_summaries.items():
        aggregate[architecture] = {
            "repetitions": len(summaries),
            "mean_joint_exact_rate": mean(float(item["joint_exact_rate"]) for item in summaries),
            "mean_route_exact_rate": mean(float(item["route_exact_rate"]) for item in summaries),
            "mean_filter_joint_exact_rate": mean(
                float(item["filter_joint_exact_rate"]) for item in summaries
            ),
            "worst_joint_exact_rate": min(float(item["joint_exact_rate"]) for item in summaries),
            "schema_violations": sum(int(item["schema_violations"]) for item in summaries),
            "llm_calls": sum(int(item["llm_calls"]) for item in summaries),
            "input_tokens": sum(int(item["input_tokens"]) for item in summaries),
            "output_tokens": sum(int(item["output_tokens"]) for item in summaries),
        }

    return {
        "cases": len(suite.cases),
        "requested_llm_repeats": repeats,
        "architectures": [architecture.value for architecture in SemanticArchitecture],
        "repetition_summaries": dict(repetition_summaries),
        "aggregate": aggregate,
        "stability": stability,
        "rows": dict(architecture_rows),
        "governance": {
            "jh4_is_known_development_material": True,
            "not_a_generalization_claim": True,
            "retriever_called": False,
            "sql_executed": False,
            "external_tools_available_to_llm": False,
            "production_graph_modified": False,
        },
    }
