from __future__ import annotations

import argparse
import json
from pathlib import Path

from cpgf.ai import plan_knowledge_retrieval, route_question
from cpgf.benchmark import (
    benchmark_sha256,
    evaluate_retrieval_planner,
    joint_holdout_sha256,
    load_joint_retrieval_holdout,
    load_retrieval_benchmark,
)
from cpgf.version import RETRIEVAL_PLANNER_VERSION, ROUTER_VERSION

DEVELOPMENT = Path("data/benchmarks/knowledge_retrieval_v1_0_0.csv")
KNOWN_HOLDOUT = Path("data/benchmarks/retrieval_planner_holdout_v1_0_0.csv")
JOINT_HOLDOUT = Path("data/benchmarks/joint_retrieval_holdout_v2_0_0.csv")
ROUTER_MANIFEST = Path("data/manifests/assistant_router_1_3_0.json")


def _evaluate_retrieval(path: Path) -> dict[str, object]:
    suite = load_retrieval_benchmark(path)
    result = evaluate_retrieval_planner(suite, plan_knowledge_retrieval)
    divergent = [
        row["id"] for row in result["cases_detail"] if not bool(row["joint_exact"])
    ]
    return {
        "path": str(path),
        "sha256": benchmark_sha256(path),
        "result": result,
        "joint_divergent_ids": divergent,
    }


def _evaluate_joint() -> dict[str, object]:
    suite = load_joint_retrieval_holdout(JOINT_HOLDOUT)
    details: list[dict[str, object]] = []

    for case in suite.cases:
        decision = route_question(case.question)
        plan = plan_knowledge_retrieval(case.question, decision=decision)
        expected_scopes = {item.value for item in case.expected_scopes}
        predicted_scopes = {item.value for item in plan.scopes}
        expected_temporal = {item.value for item in case.expected_temporal_statuses}
        predicted_temporal = {item.value for item in plan.temporal_statuses}
        route_exact = decision.route == case.expected_route
        scope_exact = expected_scopes == predicted_scopes
        temporal_exact = expected_temporal == predicted_temporal
        filter_joint_exact = scope_exact and temporal_exact
        details.append(
            {
                "id": case.id,
                "expected_route": case.expected_route.value,
                "actual_route": decision.route.value,
                "route_exact": route_exact,
                "expected_scopes": sorted(expected_scopes),
                "predicted_scopes": sorted(predicted_scopes),
                "scope_exact": scope_exact,
                "expected_temporal_statuses": sorted(expected_temporal),
                "predicted_temporal_statuses": sorted(predicted_temporal),
                "temporal_exact": temporal_exact,
                "filter_joint_exact": filter_joint_exact,
                "joint_exact": route_exact and filter_joint_exact,
            }
        )

    return {
        "path": str(JOINT_HOLDOUT),
        "sha256": joint_holdout_sha256(JOINT_HOLDOUT),
        "cases": len(details),
        "route_exact": sum(bool(row["route_exact"]) for row in details),
        "scope_exact": sum(bool(row["scope_exact"]) for row in details),
        "temporal_exact": sum(bool(row["temporal_exact"]) for row in details),
        "filter_joint_exact": sum(bool(row["filter_joint_exact"]) for row in details),
        "joint_exact": sum(bool(row["joint_exact"]) for row in details),
        "route_error_ids": [row["id"] for row in details if not bool(row["route_exact"])],
        "scope_error_ids": [row["id"] for row in details if not bool(row["scope_exact"])],
        "temporal_error_ids": [
            row["id"] for row in details if not bool(row["temporal_exact"])
        ],
        "filter_error_ids": [
            row["id"] for row in details if not bool(row["filter_joint_exact"])
        ],
        "joint_error_ids": [row["id"] for row in details if not bool(row["joint_exact"])],
        "cases_detail": details,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Avalia o Planner 1.2.0 em conjuntos conhecidos, preservando o Router 1.3 "
            "como contexto histórico de seu tuning e permitindo Router corrente posterior."
        )
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    router_manifest = json.loads(ROUTER_MANIFEST.read_text(encoding="utf-8"))
    payload = {
        "artifact": "retrieval_planner_1_2_regression",
        "status": "KNOWN_REGRESSION_ONLY",
        "router_version_held_fixed": router_manifest["router_version"],
        "current_router_version": ROUTER_VERSION,
        "planner_version": RETRIEVAL_PLANNER_VERSION,
        "development": _evaluate_retrieval(DEVELOPMENT),
        "known_holdout": _evaluate_retrieval(KNOWN_HOLDOUT),
        "joint_holdout_v2_known_regression": _evaluate_joint(),
        "baseline_before_planner_1_2": {
            "router_version": router_manifest["router_version"],
            "planner_version": router_manifest["planner_version_held_fixed"],
            "route_exact": router_manifest["known_regression_sets"]["joint_holdout_v2"][
                "route_exact"
            ],
            "filter_joint_exact": router_manifest["known_regression_sets"][
                "joint_holdout_v2"
            ]["filter_joint_exact_with_planner_1_1"],
            "remaining_filter_error_ids": router_manifest["known_regression_sets"][
                "joint_holdout_v2"
            ]["remaining_filter_error_ids"],
        },
        "governance": {
            "all_evaluation_sets_known_before_planner_1_2_tuning": True,
            "joint_holdout_v2_is_known_regression": True,
            "router_modified_during_planner_1_2_tuning": False,
            "historical_router_1_3_context_preserved": True,
            "current_router_may_advance": True,
            "case_id_specific_rules_added": False,
            "new_generalization_claim": False,
            "llm_called": False,
            "sql_executed": False,
            "retriever_called": False,
            "external_embeddings_called": False,
        },
    }
    args.output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
