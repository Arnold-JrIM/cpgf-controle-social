from __future__ import annotations

from collections import Counter, defaultdict
from statistics import mean

from pydantic import BaseModel, ConfigDict

from cpgf.ai.retrieval_planner import plan_knowledge_retrieval
from cpgf.ai.router import RouteDecision, route_question
from cpgf.ai.semantic_experiment import SemanticProvider
from cpgf.benchmark.joint_retrieval_v5 import (
    JointRetrievalHoldoutV5Case,
    JointRetrievalHoldoutV5Suite,
)


class JH5Prediction(BaseModel):
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


def _deterministic_prediction(question: str) -> JH5Prediction:
    decision = route_question(question)
    plan = plan_knowledge_retrieval(question, decision=decision)
    return JH5Prediction(
        route=decision.route.value,
        scopes=tuple(scope.value for scope in plan.scopes),
        temporal_statuses=tuple(status.value for status in plan.temporal_statuses),
        llm_called=False,
    )


def _candidate_prediction(question: str, provider: SemanticProvider) -> JH5Prediction:
    call = provider.classify_route(question)
    decision = RouteDecision(
        route=call.output.route,
        reason=call.output.reason,
        deterministic=False,
    )
    plan = plan_knowledge_retrieval(question, decision=decision)
    metadata = call.metadata
    return JH5Prediction(
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


def _failed_candidate_prediction(exc: Exception) -> JH5Prediction:
    return JH5Prediction(
        route="__invalid__",
        scopes=(),
        temporal_statuses=(),
        llm_called=True,
        schema_valid=False,
        error=f"{type(exc).__name__}: {exc}",
    )


def _exactness(
    case: JointRetrievalHoldoutV5Case,
    prediction: JH5Prediction,
) -> dict[str, bool]:
    expected_scopes = {scope.value for scope in case.expected_scopes}
    expected_temporal = {status.value for status in case.expected_temporal_statuses}
    route_exact = case.expected_route.value == prediction.route
    scope_exact = expected_scopes == set(prediction.scopes)
    temporal_exact = expected_temporal == set(prediction.temporal_statuses)
    return {
        "route_exact": route_exact,
        "scope_exact": scope_exact,
        "temporal_exact": temporal_exact,
        "filter_joint_exact": scope_exact and temporal_exact,
        "joint_exact": route_exact and scope_exact and temporal_exact,
    }


def _row(
    *,
    architecture: str,
    repeat: int,
    case: JointRetrievalHoldoutV5Case,
    prediction: JH5Prediction,
) -> dict[str, object]:
    return {
        "architecture": architecture,
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
        **_exactness(case, prediction),
    }


def _summary(rows: list[dict[str, object]]) -> dict[str, object]:
    cases = len(rows)
    metrics = (
        "route_exact",
        "scope_exact",
        "temporal_exact",
        "filter_joint_exact",
        "joint_exact",
    )
    result: dict[str, object] = {"cases": cases}
    for metric in metrics:
        count = sum(bool(row[metric]) for row in rows)
        result[metric] = count
        result[f"{metric}_rate"] = count / cases if cases else 0.0

    schema_violations = sum(not bool(row["schema_valid"]) for row in rows)
    result["schema_violations"] = schema_violations
    result["llm_calls"] = sum(bool(row["llm_called"]) for row in rows)
    result["input_tokens"] = sum(int(row["input_tokens"] or 0) for row in rows)
    result["output_tokens"] = sum(int(row["output_tokens"] or 0) for row in rows)
    latencies = [
        float(row["latency_ms"])
        for row in rows
        if row["latency_ms"] is not None
    ]
    result["mean_latency_ms"] = mean(latencies) if latencies else 0.0
    return result


def _category_summaries(rows: list[dict[str, object]]) -> dict[str, dict[str, object]]:
    grouped: defaultdict[str, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        grouped[str(row["category"])].append(row)
    return {category: _summary(items) for category, items in sorted(grouped.items())}


def evaluate_candidate_b_jh5(
    suite: JointRetrievalHoldoutV5Suite,
    *,
    provider: SemanticProvider,
    repeats: int = 3,
) -> dict[str, object]:
    if repeats != 3:
        raise ValueError("JH5 exige exatamente três repetições da candidata B")

    baseline_rows: list[dict[str, object]] = []
    for case in suite.cases:
        baseline_rows.append(
            _row(
                architecture="A_deterministic",
                repeat=1,
                case=case,
                prediction=_deterministic_prediction(case.question),
            )
        )

    candidate_rows: list[dict[str, object]] = []
    repetition_summaries: list[dict[str, object]] = []
    repetition_categories: list[dict[str, dict[str, object]]] = []
    for repeat in range(1, repeats + 1):
        rows: list[dict[str, object]] = []
        for case in suite.cases:
            try:
                prediction = _candidate_prediction(case.question, provider)
            except Exception as exc:  # erros da API/schema precisam permanecer na evidência
                prediction = _failed_candidate_prediction(exc)
            row = _row(
                architecture="B_llm_route",
                repeat=repeat,
                case=case,
                prediction=prediction,
            )
            rows.append(row)
            candidate_rows.append(row)
        repetition_summaries.append(_summary(rows))
        repetition_categories.append(_category_summaries(rows))

    signatures: defaultdict[
        str, list[tuple[str, tuple[str, ...], tuple[str, ...]]]
    ] = defaultdict(list)
    for row in candidate_rows:
        signatures[str(row["id"])].append(
            (
                str(row["predicted_route"]),
                tuple(row["predicted_scopes"]),
                tuple(row["predicted_temporal_statuses"]),
            )
        )

    modal_shares: list[float] = []
    identical_cases = 0
    for values in signatures.values():
        most_common = Counter(values).most_common(1)[0][1]
        share = most_common / len(values)
        modal_shares.append(share)
        if most_common == len(values):
            identical_cases += 1

    baseline_summary = _summary(baseline_rows)
    candidate_aggregate = {
        "repetitions": len(repetition_summaries),
        "mean_joint_exact_rate": mean(
            float(item["joint_exact_rate"]) for item in repetition_summaries
        ),
        "worst_joint_exact_rate": min(
            float(item["joint_exact_rate"]) for item in repetition_summaries
        ),
        "mean_route_exact_rate": mean(
            float(item["route_exact_rate"]) for item in repetition_summaries
        ),
        "mean_filter_joint_exact_rate": mean(
            float(item["filter_joint_exact_rate"]) for item in repetition_summaries
        ),
        "schema_violations": sum(
            int(item["schema_violations"]) for item in repetition_summaries
        ),
        "llm_calls": sum(int(item["llm_calls"]) for item in repetition_summaries),
        "input_tokens": sum(int(item["input_tokens"]) for item in repetition_summaries),
        "output_tokens": sum(
            int(item["output_tokens"]) for item in repetition_summaries
        ),
        "mean_latency_ms": mean(
            float(item["mean_latency_ms"]) for item in repetition_summaries
        ),
    }

    categories = sorted(repetition_categories[0])
    category_aggregate: dict[str, dict[str, object]] = {}
    for category in categories:
        category_aggregate[category] = {
            "cases_per_repetition": int(repetition_categories[0][category]["cases"]),
            "mean_joint_exact_rate": mean(
                float(item[category]["joint_exact_rate"])
                for item in repetition_categories
            ),
            "mean_route_exact_rate": mean(
                float(item[category]["route_exact_rate"])
                for item in repetition_categories
            ),
            "mean_filter_joint_exact_rate": mean(
                float(item[category]["filter_joint_exact_rate"])
                for item in repetition_categories
            ),
        }

    response_models = Counter(
        str(row["response_model"])
        for row in candidate_rows
        if row["response_model"] is not None
    )
    errors = [
        {
            "repeat": row["repeat"],
            "id": row["id"],
            "error": row["error"],
        }
        for row in candidate_rows
        if row["error"] is not None
    ]

    return {
        "cases": len(suite.cases),
        "architectures": ["A_deterministic", "B_llm_route"],
        "baseline_A": {
            "summary": baseline_summary,
            "categories": _category_summaries(baseline_rows),
            "rows": baseline_rows,
        },
        "candidate_B": {
            "requested_repetitions": repeats,
            "repetition_summaries": repetition_summaries,
            "repetition_categories": repetition_categories,
            "aggregate": candidate_aggregate,
            "categories": category_aggregate,
            "stability": {
                "mean_modal_share": mean(modal_shares) if modal_shares else 0.0,
                "all_repetitions_identical_cases": identical_cases,
                "cases": len(signatures),
            },
            "response_models": dict(sorted(response_models.items())),
            "errors": errors,
            "rows": candidate_rows,
        },
        "governance": {
            "jh5_is_independent_candidate_holdout": True,
            "retriever_called": False,
            "sql_executed": False,
            "external_tools_available_to_llm": False,
            "final_answer_llm_called": False,
            "production_graph_modified": False,
        },
    }


def evaluate_jh5_acceptance_gate(
    evaluation: dict[str, object],
    rules: dict[str, object],
) -> dict[str, object]:
    baseline = evaluation["baseline_A"]["summary"]
    candidate = evaluation["candidate_B"]
    aggregate = candidate["aggregate"]
    stability = candidate["stability"]
    categories = candidate["categories"]

    baseline_joint = float(baseline["joint_exact_rate"])
    candidate_joint = float(aggregate["mean_joint_exact_rate"])
    gain = candidate_joint - baseline_joint

    category_checks = {
        category: float(stats["mean_joint_exact_rate"])
        >= float(rules["minimum_each_category_B_mean_joint_exact_rate"])
        for category, stats in categories.items()
    }
    checks = {
        "all_three_repetitions_completed": int(aggregate["repetitions"]) == 3
        and all(int(item["cases"]) == 48 for item in candidate["repetition_summaries"]),
        "zero_schema_violations": int(aggregate["schema_violations"])
        == int(rules["schema_violations_allowed"]),
        "minimum_B_mean_joint_exact_rate": candidate_joint
        >= float(rules["minimum_B_mean_joint_exact_rate"]),
        "minimum_B_absolute_joint_gain_over_A": gain
        >= float(rules["minimum_B_absolute_joint_gain_over_A"]),
        "minimum_B_mean_route_exact_rate": float(aggregate["mean_route_exact_rate"])
        >= float(rules["minimum_B_mean_route_exact_rate"]),
        "minimum_B_mean_modal_stability": float(stability["mean_modal_share"])
        >= float(rules["minimum_B_mean_modal_stability"]),
        "minimum_each_category_B_mean_joint_exact_rate": all(category_checks.values()),
    }
    return {
        "passed": all(checks.values()),
        "checks": checks,
        "category_checks": category_checks,
        "observed": {
            "A_joint_exact_rate": baseline_joint,
            "B_mean_joint_exact_rate": candidate_joint,
            "B_absolute_joint_gain_over_A": gain,
            "B_mean_route_exact_rate": aggregate["mean_route_exact_rate"],
            "B_mean_modal_stability": stability["mean_modal_share"],
            "B_schema_violations": aggregate["schema_violations"],
            "B_category_mean_joint_exact_rate": {
                category: stats["mean_joint_exact_rate"]
                for category, stats in categories.items()
            },
        },
        "rules": rules,
        "interpretation": (
            "PASS no gate prospectivo de generalização"
            if all(checks.values())
            else "FAIL no gate prospectivo; resultado deve ser preservado sem tuning retrospectivo"
        ),
    }
