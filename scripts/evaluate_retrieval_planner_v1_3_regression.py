from __future__ import annotations

import argparse
import hashlib
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
from cpgf.benchmark.joint_retrieval_v3 import load_joint_retrieval_holdout_v3
from cpgf.version import RETRIEVAL_PLANNER_VERSION, ROUTER_VERSION

DEVELOPMENT = Path("data/benchmarks/knowledge_retrieval_v1_0_0.csv")
KNOWN_HOLDOUT = Path("data/benchmarks/retrieval_planner_holdout_v1_0_0.csv")
JH2 = Path("data/benchmarks/joint_retrieval_holdout_v2_0_0.csv")
JH3 = Path("data/benchmarks/joint_retrieval_holdout_v3_0_0.csv")
ROUTER_MANIFEST = Path("data/manifests/assistant_router_1_4_0.json")
ROUTER_SOURCE = Path("src/cpgf/ai/router.py")
PLANNER_SOURCE = Path("src/cpgf/ai/retrieval_planner.py")


def _git_blob_sha(path: Path) -> str:
    content = path.read_bytes()
    return hashlib.sha1(f"blob {len(content)}\0".encode() + content).hexdigest()


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


def _evaluate_jh2() -> dict[str, object]:
    suite = load_joint_retrieval_holdout(JH2)
    rows: list[dict[str, object]] = []
    for case in suite.cases:
        decision = route_question(case.question)
        plan = plan_knowledge_retrieval(case.question, decision=decision)
        expected_scopes = {item.value for item in case.expected_scopes}
        expected_temporal = {item.value for item in case.expected_temporal_statuses}
        predicted_scopes = {item.value for item in plan.scopes}
        predicted_temporal = {item.value for item in plan.temporal_statuses}
        route_exact = decision.route == case.expected_route
        scope_exact = predicted_scopes == expected_scopes
        temporal_exact = predicted_temporal == expected_temporal
        rows.append(
            {
                "id": case.id,
                "route_exact": route_exact,
                "scope_exact": scope_exact,
                "temporal_exact": temporal_exact,
                "joint_exact": route_exact and scope_exact and temporal_exact,
            }
        )
    return {
        "path": str(JH2),
        "sha256": joint_holdout_sha256(JH2),
        "cases": len(rows),
        "route_exact": sum(bool(row["route_exact"]) for row in rows),
        "scope_exact": sum(bool(row["scope_exact"]) for row in rows),
        "temporal_exact": sum(bool(row["temporal_exact"]) for row in rows),
        "joint_exact": sum(bool(row["joint_exact"]) for row in rows),
        "joint_error_ids": [row["id"] for row in rows if not bool(row["joint_exact"])],
    }


def _evaluate_jh3() -> dict[str, object]:
    suite = load_joint_retrieval_holdout_v3(JH3)
    rows: list[dict[str, object]] = []
    for case in suite.cases:
        decision = route_question(case.question)
        plan = plan_knowledge_retrieval(case.question, decision=decision)
        expected_scopes = {item.value for item in case.expected_scopes}
        expected_temporal = {item.value for item in case.expected_temporal_statuses}
        predicted_scopes = {item.value for item in plan.scopes}
        predicted_temporal = {item.value for item in plan.temporal_statuses}
        route_exact = decision.route == case.expected_route
        scope_exact = predicted_scopes == expected_scopes
        temporal_exact = predicted_temporal == expected_temporal
        joint_exact = route_exact and scope_exact and temporal_exact
        rows.append(
            {
                "id": case.id,
                "category": case.category.value,
                "expected_route": case.expected_route.value,
                "actual_route": decision.route.value,
                "route_exact": route_exact,
                "expected_scopes": sorted(expected_scopes),
                "predicted_scopes": sorted(predicted_scopes),
                "scope_exact": scope_exact,
                "expected_temporal_statuses": sorted(expected_temporal),
                "predicted_temporal_statuses": sorted(predicted_temporal),
                "temporal_exact": temporal_exact,
                "joint_exact": joint_exact,
            }
        )
    return {
        "path": str(JH3),
        "cases": len(rows),
        "route_exact": sum(bool(row["route_exact"]) for row in rows),
        "scope_exact": sum(bool(row["scope_exact"]) for row in rows),
        "temporal_exact": sum(bool(row["temporal_exact"]) for row in rows),
        "joint_exact": sum(bool(row["joint_exact"]) for row in rows),
        "route_error_ids": [row["id"] for row in rows if not bool(row["route_exact"])],
        "scope_error_ids": [row["id"] for row in rows if not bool(row["scope_exact"])],
        "temporal_error_ids": [row["id"] for row in rows if not bool(row["temporal_exact"])],
        "joint_error_ids": [row["id"] for row in rows if not bool(row["joint_exact"])],
        "rows": rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Avalia Planner 1.3.0 somente em regressões conhecidas, com Router 1.4.0 "
            "congelado. Não produz nova evidência de generalização."
        )
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    router_manifest = json.loads(ROUTER_MANIFEST.read_text(encoding="utf-8"))
    current_router_blob = _git_blob_sha(ROUTER_SOURCE)
    if ROUTER_VERSION != "1.4.0":
        raise ValueError("Planner 1.3 exige Router 1.4.0 congelado")
    if current_router_blob != "89150b97e9c87d9af0d0b0f888870dcc74ef86b1":
        raise ValueError("Blob do Router 1.4 mudou durante tuning exclusivo do Planner")
    if RETRIEVAL_PLANNER_VERSION != "1.3.0":
        raise ValueError("Versão operacional do Planner deve ser 1.3.0")

    jh3 = _evaluate_jh3()
    baseline = router_manifest["known_regression_sets"]["joint_holdout_v3"]
    payload = {
        "artifact": "retrieval_planner_v1_3_known_regression",
        "status": "KNOWN_REGRESSION_ONLY",
        "router_version_held_fixed": ROUTER_VERSION,
        "router_source_git_blob_sha": current_router_blob,
        "planner_version": RETRIEVAL_PLANNER_VERSION,
        "planner_source_git_blob_sha": _git_blob_sha(PLANNER_SOURCE),
        "development": _evaluate_retrieval(DEVELOPMENT),
        "known_holdout": _evaluate_retrieval(KNOWN_HOLDOUT),
        "joint_holdout_v2_known_regression": _evaluate_jh2(),
        "joint_holdout_v3_known_regression": jh3,
        "baseline_before_planner_1_3": {
            "router_version": router_manifest["router_version"],
            "planner_version": router_manifest["planner_version_held_fixed"],
            "route_exact": baseline["route_exact"],
            "scope_exact": baseline["scope_exact"],
            "temporal_exact": baseline["temporal_exact"],
            "joint_exact": baseline["joint_exact"],
            "remaining_joint_error_ids": baseline["joint_error_ids"],
        },
        "governance": {
            "all_evaluation_sets_known_before_planner_1_3_tuning": True,
            "jh2_is_known_regression": True,
            "jh3_is_known_regression": True,
            "router_modified_in_increment": False,
            "router_blob_preserved": True,
            "case_id_specific_rules_added": False,
            "planner_rules_are_deterministic": True,
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
