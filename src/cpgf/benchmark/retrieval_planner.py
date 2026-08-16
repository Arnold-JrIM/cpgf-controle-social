from __future__ import annotations

from collections import Counter
from collections.abc import Callable

from cpgf.ai.retrieval_planner import RetrievalPlan

from .retrieval import RetrievalBenchmarkSuite

Planner = Callable[[str], RetrievalPlan]


def _recall(expected: set[str], predicted: set[str]) -> float:
    if not expected:
        return 1.0
    return len(expected.intersection(predicted)) / len(expected)


def _precision(expected: set[str], predicted: set[str]) -> float:
    if not predicted:
        return 1.0 if not expected else 0.0
    return len(expected.intersection(predicted)) / len(predicted)


def evaluate_retrieval_planner(
    suite: RetrievalBenchmarkSuite,
    planner: Planner,
) -> dict[str, object]:
    """Compara filtros inferidos com o oráculo sem expor o oráculo ao planner."""
    rows: list[dict[str, object]] = []
    scope_exact = 0
    temporal_exact = 0
    joint_exact = 0
    scope_recalls: list[float] = []
    scope_precisions: list[float] = []
    temporal_recalls: list[float] = []
    temporal_precisions: list[float] = []
    route_counts: Counter[str] = Counter()

    for case in suite.cases:
        plan = planner(case.question)
        expected_scopes = {scope.value for scope in case.expected_scopes}
        predicted_scopes = {scope.value for scope in plan.scopes}
        expected_temporal = {status.value for status in case.expected_temporal_statuses}
        predicted_temporal = {status.value for status in plan.temporal_statuses}

        scope_is_exact = expected_scopes == predicted_scopes
        temporal_is_exact = expected_temporal == predicted_temporal
        scope_exact += int(scope_is_exact)
        temporal_exact += int(temporal_is_exact)
        joint_exact += int(scope_is_exact and temporal_is_exact)
        scope_recalls.append(_recall(expected_scopes, predicted_scopes))
        scope_precisions.append(_precision(expected_scopes, predicted_scopes))
        temporal_recalls.append(_recall(expected_temporal, predicted_temporal))
        temporal_precisions.append(_precision(expected_temporal, predicted_temporal))
        route_counts[plan.route.value] += 1

        rows.append(
            {
                "id": case.id,
                "route": plan.route.value,
                "expected_scopes": sorted(expected_scopes),
                "predicted_scopes": sorted(predicted_scopes),
                "expected_temporal_statuses": sorted(expected_temporal),
                "predicted_temporal_statuses": sorted(predicted_temporal),
                "scope_exact": scope_is_exact,
                "temporal_exact": temporal_is_exact,
                "joint_exact": scope_is_exact and temporal_is_exact,
                "trail_hints": list(plan.trail_hints),
            }
        )

    total = len(rows)
    denominator = max(total, 1)
    return {
        "cases": total,
        "scope_exact_match_rate": scope_exact / denominator,
        "temporal_exact_match_rate": temporal_exact / denominator,
        "joint_exact_match_rate": joint_exact / denominator,
        "mean_scope_recall": sum(scope_recalls) / denominator,
        "mean_scope_precision": sum(scope_precisions) / denominator,
        "mean_temporal_recall": sum(temporal_recalls) / denominator,
        "mean_temporal_precision": sum(temporal_precisions) / denominator,
        "route_counts": dict(sorted(route_counts.items())),
        "cases_detail": rows,
        "governance": {
            "planner_input_is_question_only": True,
            "benchmark_oracle_used_only_for_post_hoc_evaluation": True,
        },
    }
