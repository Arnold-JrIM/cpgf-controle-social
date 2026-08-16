from __future__ import annotations

from collections import Counter, defaultdict

from cpgf.ai import Route, RouteDecision, plan_knowledge_retrieval, route_question

from .joint_retrieval_attribution import (
    DOCUMENTARY_ROUTES,
    JointRetrievalFlowAttribution,
)
from .joint_retrieval_v4 import JointRetrievalHoldoutV4Case, JointRetrievalHoldoutV4Suite


def _counterfactual_decision(route: Route) -> RouteDecision:
    return RouteDecision(
        route=route,
        reason="rota contrafactual para diagnóstico post-hoc do Joint Holdout 4.0",
    )


def _filter_exactness(
    case: JointRetrievalHoldoutV4Case,
    plan: object,
) -> dict[str, object]:
    expected_scopes = {scope.value for scope in case.expected_scopes}
    expected_temporal = {status.value for status in case.expected_temporal_statuses}
    predicted_scopes = {scope.value for scope in plan.scopes}
    predicted_temporal = {status.value for status in plan.temporal_statuses}
    scope_exact = expected_scopes == predicted_scopes
    temporal_exact = expected_temporal == predicted_temporal
    return {
        "expected_scopes": sorted(expected_scopes),
        "predicted_scopes": sorted(predicted_scopes),
        "scope_exact": scope_exact,
        "expected_temporal_statuses": sorted(expected_temporal),
        "predicted_temporal_statuses": sorted(predicted_temporal),
        "temporal_exact": temporal_exact,
        "filter_joint_exact": scope_exact and temporal_exact,
    }


def _attribute(
    *,
    route_exact: bool,
    actual_filter_joint_exact: bool,
    expected_route_filter_joint_exact: bool,
) -> JointRetrievalFlowAttribution:
    if route_exact and actual_filter_joint_exact:
        return JointRetrievalFlowAttribution.PASS
    if route_exact:
        return JointRetrievalFlowAttribution.PLANNER_ONLY
    if expected_route_filter_joint_exact:
        return JointRetrievalFlowAttribution.ROUTER_ONLY
    return JointRetrievalFlowAttribution.ROUTER_AND_PLANNER


def evaluate_joint_retrieval_flow_attribution_v4(
    suite: JointRetrievalHoldoutV4Suite,
) -> dict[str, object]:
    """Decompõe post-hoc as falhas do JH4 sem alterar Router ou Planner."""

    rows: list[dict[str, object]] = []
    attribution_counts: Counter[str] = Counter()
    ids_by_attribution: defaultdict[str, list[str]] = defaultdict(list)
    by_category: defaultdict[str, Counter[str]] = defaultdict(Counter)

    for case in suite.cases:
        actual_decision = route_question(case.question)
        actual_plan = plan_knowledge_retrieval(case.question, decision=actual_decision)
        actual_filters = _filter_exactness(case, actual_plan)
        route_exact = actual_decision.route == case.expected_route
        actual_joint_exact = route_exact and bool(actual_filters["filter_joint_exact"])

        counterfactuals: dict[str, dict[str, object]] = {}
        exact_filter_routes: list[Route] = []
        for route in DOCUMENTARY_ROUTES:
            plan = plan_knowledge_retrieval(
                case.question,
                decision=_counterfactual_decision(route),
            )
            outcome = _filter_exactness(case, plan)
            counterfactuals[route.value] = outcome
            if bool(outcome["filter_joint_exact"]):
                exact_filter_routes.append(route)

        expected_route_outcome = counterfactuals[case.expected_route.value]
        attribution = _attribute(
            route_exact=route_exact,
            actual_filter_joint_exact=bool(actual_filters["filter_joint_exact"]),
            expected_route_filter_joint_exact=bool(
                expected_route_outcome["filter_joint_exact"]
            ),
        )
        attribution_counts[attribution.value] += 1
        ids_by_attribution[attribution.value].append(case.id)
        by_category[case.category.value][attribution.value] += 1

        rows.append(
            {
                "id": case.id,
                "category": case.category.value,
                "expected_route": case.expected_route.value,
                "actual_route": actual_decision.route.value,
                "route_exact": route_exact,
                "actual_filters": actual_filters,
                "actual_joint_exact": actual_joint_exact,
                "expected_route_counterfactual": expected_route_outcome,
                "expected_route_correction_recovers_joint": (
                    not route_exact
                    and bool(expected_route_outcome["filter_joint_exact"])
                ),
                "exact_filter_counterfactual_routes": [
                    route.value for route in exact_filter_routes
                ],
                "counterfactuals": counterfactuals,
                "attribution": attribution.value,
            }
        )

    router_only = attribution_counts[JointRetrievalFlowAttribution.ROUTER_ONLY.value]
    planner_only = attribution_counts[JointRetrievalFlowAttribution.PLANNER_ONLY.value]
    shared = attribution_counts[
        JointRetrievalFlowAttribution.ROUTER_AND_PLANNER.value
    ]
    passes = attribution_counts[JointRetrievalFlowAttribution.PASS.value]
    failures = len(rows) - passes

    route_wrong_filters_exact = sum(
        (not bool(row["route_exact"]))
        and bool(row["actual_filters"]["filter_joint_exact"])
        for row in rows
    )
    route_exact_filters_wrong = sum(
        bool(row["route_exact"])
        and not bool(row["actual_filters"]["filter_joint_exact"])
        for row in rows
    )
    route_wrong_filters_wrong = sum(
        (not bool(row["route_exact"]))
        and not bool(row["actual_filters"]["filter_joint_exact"])
        for row in rows
    )

    expected_route_filter_exact = sum(
        bool(row["expected_route_counterfactual"]["filter_joint_exact"])
        for row in rows
    )
    any_route_filter_exact = sum(
        bool(row["exact_filter_counterfactual_routes"]) for row in rows
    )

    return {
        "cases": len(rows),
        "actual_joint_exact": passes,
        "actual_joint_failures": failures,
        "documentary_routes_swept": [route.value for route in DOCUMENTARY_ROUTES],
        "attribution_counts": dict(sorted(attribution_counts.items())),
        "ids_by_attribution": {
            key: value for key, value in sorted(ids_by_attribution.items())
        },
        "attribution_by_category": {
            category: dict(sorted(counts.items()))
            for category, counts in sorted(by_category.items())
        },
        "router_only_failures": router_only,
        "planner_only_failures": planner_only,
        "shared_router_planner_failures": shared,
        "router_contribution_to_joint_failures": router_only + shared,
        "planner_contribution_to_joint_failures": planner_only + shared,
        "best_case_joint_exact_with_expected_route_correction_only": passes
        + router_only,
        "best_case_joint_exact_rate_with_expected_route_correction_only": (
            (passes + router_only) / len(rows) if rows else 0.0
        ),
        "expected_route_filter_exact_cases": expected_route_filter_exact,
        "any_documentary_route_filter_exact_cases": any_route_filter_exact,
        "observed_layer_mismatch_reproduction": {
            "route_wrong_filters_exact": route_wrong_filters_exact,
            "route_exact_filters_wrong": route_exact_filters_wrong,
            "route_wrong_filters_wrong": route_wrong_filters_wrong,
            "clean_passes": passes,
        },
        "cases_detail": rows,
        "governance": {
            "diagnostic_is_post_hoc": True,
            "joint_holdout_4_is_already_known": True,
            "first_independent_measurement_preserved": True,
            "router_rules_modified": False,
            "planner_rules_modified": False,
            "question_and_oracle_held_fixed": True,
            "counterfactual_changes_only_route_decision": True,
            "primary_attribution_uses_expected_route_counterfactual": True,
            "all_documentary_routes_swept_for_secondary_diagnostics": True,
            "not_a_new_generalization_claim": True,
            "llm_called": False,
            "sql_executed": False,
            "retriever_called": False,
            "external_embeddings_called": False,
        },
    }
