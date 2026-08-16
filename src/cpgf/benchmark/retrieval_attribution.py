from __future__ import annotations

from collections import Counter, defaultdict
from enum import StrEnum

from cpgf.ai import Route, RouteDecision, plan_knowledge_retrieval, route_question

from .retrieval import RetrievalBenchmarkCase, RetrievalBenchmarkSuite


class RetrievalFlowAttribution(StrEnum):
    PASS = "pass"
    ROUTER_LATENT = "router_latent"
    ROUTER_BLOCKING = "router_blocking"
    ROUTER_SELECTION = "router_selection"
    PLANNER = "planner"
    ROUTER_AND_PLANNER = "router_and_planner"


RETRIEVAL_CAPABLE_ROUTES: tuple[Route, ...] = (
    Route.KNOWLEDGE,
    Route.METHODOLOGY,
    Route.COMPOSITE,
)


def _counterfactual_decision(route: Route) -> RouteDecision:
    return RouteDecision(
        route=route,
        reason="rota contrafactual para diagnóstico post-hoc Router x Planner",
    )


def _plan_exactness(case: RetrievalBenchmarkCase, plan: object) -> dict[str, object]:
    expected_scopes = {scope.value for scope in case.expected_scopes}
    expected_temporal = {status.value for status in case.expected_temporal_statuses}
    predicted_scopes = {scope.value for scope in plan.scopes}
    predicted_temporal = {status.value for status in plan.temporal_statuses}
    scope_exact = expected_scopes == predicted_scopes
    temporal_exact = expected_temporal == predicted_temporal
    return {
        "expected_scopes": sorted(expected_scopes),
        "predicted_scopes": sorted(predicted_scopes),
        "expected_temporal_statuses": sorted(expected_temporal),
        "predicted_temporal_statuses": sorted(predicted_temporal),
        "scope_exact": scope_exact,
        "temporal_exact": temporal_exact,
        "joint_exact": scope_exact and temporal_exact,
    }


def _attribute(
    *,
    actual_joint_exact: bool,
    actual_route_capable: bool,
    actual_route: Route,
    exact_counterfactual_routes: tuple[Route, ...],
) -> RetrievalFlowAttribution:
    if actual_joint_exact:
        if actual_route_capable:
            return RetrievalFlowAttribution.PASS
        return RetrievalFlowAttribution.ROUTER_LATENT

    if not actual_route_capable:
        if exact_counterfactual_routes:
            return RetrievalFlowAttribution.ROUTER_BLOCKING
        return RetrievalFlowAttribution.ROUTER_AND_PLANNER

    if any(route != actual_route for route in exact_counterfactual_routes):
        return RetrievalFlowAttribution.ROUTER_SELECTION
    return RetrievalFlowAttribution.PLANNER


def evaluate_retrieval_flow_attribution(
    suite: RetrievalBenchmarkSuite,
) -> dict[str, object]:
    """Decompõe post-hoc a contribuição do Router e do Planner sem alterar suas regras.

    O diagnóstico usa um sweep contrafactual somente sobre rotas capazes de acionar
    recuperação documental/metodológica. Pergunta e oráculo permanecem fixos.
    """

    rows: list[dict[str, object]] = []
    attribution_counts: Counter[str] = Counter()
    ids_by_attribution: defaultdict[str, list[str]] = defaultdict(list)

    for case in suite.cases:
        actual_decision = route_question(case.question)
        actual_plan = plan_knowledge_retrieval(case.question, decision=actual_decision)
        actual = _plan_exactness(case, actual_plan)
        actual_route_capable = actual_decision.route in RETRIEVAL_CAPABLE_ROUTES

        counterfactuals: dict[str, dict[str, object]] = {}
        exact_counterfactual_routes: list[Route] = []
        for route in RETRIEVAL_CAPABLE_ROUTES:
            plan = plan_knowledge_retrieval(
                case.question,
                decision=_counterfactual_decision(route),
            )
            outcome = _plan_exactness(case, plan)
            counterfactuals[route.value] = outcome
            if bool(outcome["joint_exact"]):
                exact_counterfactual_routes.append(route)

        exact_routes = tuple(exact_counterfactual_routes)
        attribution = _attribute(
            actual_joint_exact=bool(actual["joint_exact"]),
            actual_route_capable=actual_route_capable,
            actual_route=actual_decision.route,
            exact_counterfactual_routes=exact_routes,
        )
        attribution_counts[attribution.value] += 1
        ids_by_attribution[attribution.value].append(case.id)

        rows.append(
            {
                "id": case.id,
                "category": case.category.value,
                "actual_route": actual_decision.route.value,
                "actual_route_retrieval_capable": actual_route_capable,
                "actual": actual,
                "exact_counterfactual_routes": [route.value for route in exact_routes],
                "counterfactuals": counterfactuals,
                "attribution": attribution.value,
            }
        )

    joint_failures = [row for row in rows if not bool(row["actual"]["joint_exact"])]
    router_failure_attributions = {
        RetrievalFlowAttribution.ROUTER_BLOCKING.value,
        RetrievalFlowAttribution.ROUTER_SELECTION.value,
        RetrievalFlowAttribution.ROUTER_AND_PLANNER.value,
    }
    planner_failure_attributions = {
        RetrievalFlowAttribution.PLANNER.value,
        RetrievalFlowAttribution.ROUTER_AND_PLANNER.value,
    }

    router_contribution = sum(
        row["attribution"] in router_failure_attributions for row in joint_failures
    )
    planner_contribution = sum(
        row["attribution"] in planner_failure_attributions for row in joint_failures
    )

    return {
        "cases": len(rows),
        "retrieval_capable_routes": [route.value for route in RETRIEVAL_CAPABLE_ROUTES],
        "joint_filter_failures": len(joint_failures),
        "joint_filter_failure_ids": [row["id"] for row in joint_failures],
        "attribution_counts": dict(sorted(attribution_counts.items())),
        "ids_by_attribution": {
            key: value for key, value in sorted(ids_by_attribution.items())
        },
        "router_contribution_to_joint_failures": router_contribution,
        "planner_contribution_to_joint_failures": planner_contribution,
        "shared_router_planner_failures": attribution_counts[
            RetrievalFlowAttribution.ROUTER_AND_PLANNER.value
        ],
        "latent_router_issues_with_exact_filters": attribution_counts[
            RetrievalFlowAttribution.ROUTER_LATENT.value
        ],
        "clean_passes": attribution_counts[RetrievalFlowAttribution.PASS.value],
        "cases_detail": rows,
        "governance": {
            "diagnostic_is_post_hoc": True,
            "holdout_is_already_known": True,
            "router_rules_modified": False,
            "planner_rules_modified": False,
            "counterfactual_changes_only_route_decision": True,
            "question_and_oracle_held_fixed": True,
            "not_a_new_generalization_claim": True,
        },
    }
