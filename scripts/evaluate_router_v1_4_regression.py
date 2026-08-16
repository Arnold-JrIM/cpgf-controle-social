from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from cpgf.ai import plan_knowledge_retrieval, route_question
from cpgf.benchmark import evaluate_routing, load_benchmark, load_joint_retrieval_holdout
from cpgf.benchmark.joint_retrieval_v3 import load_joint_retrieval_holdout_v3
from cpgf.version import RETRIEVAL_PLANNER_VERSION, ROUTER_VERSION

DEVELOPMENT = Path("data/benchmarks/assistant_v1_0_0.csv")
ROUTER_HOLDOUT_V1 = Path("data/benchmarks/assistant_router_holdout_v1_0_0.csv")
ROUTER_HOLDOUT_V2 = Path("data/benchmarks/assistant_router_holdout_v2_0_0.csv")
JH2 = Path("data/benchmarks/joint_retrieval_holdout_v2_0_0.csv")
JH3 = Path("data/benchmarks/joint_retrieval_holdout_v3_0_0.csv")
JH3_MANIFEST = Path("data/manifests/joint_retrieval_holdout_3_0_0.json")
JH3_ATTRIBUTION = Path("data/manifests/joint_retrieval_flow_attribution_v3_1_0_0.json")
ROUTER_SOURCE = Path("src/cpgf/ai/router.py")
PLANNER_SOURCE = Path("src/cpgf/ai/retrieval_planner.py")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git_blob_sha(path: Path) -> str:
    content = path.read_bytes()
    return hashlib.sha1(f"blob {len(content)}\0".encode() + content).hexdigest()


def _routing_result(path: Path) -> dict[str, object]:
    result = evaluate_routing(load_benchmark(path))
    return {
        "path": str(path),
        "sha256": _sha256(path),
        "summary": result["summary"],
        "errors": [row for row in result["cases"] if not bool(row["exact"])],
    }


def _jh2_routes() -> dict[str, object]:
    suite = load_joint_retrieval_holdout(JH2)
    rows = []
    for case in suite.cases:
        decision = route_question(case.question)
        exact = decision.route == case.expected_route
        rows.append(
            {
                "id": case.id,
                "expected_route": case.expected_route.value,
                "actual_route": decision.route.value,
                "route_exact": exact,
            }
        )
    return {
        "cases": len(rows),
        "route_exact": sum(bool(row["route_exact"]) for row in rows),
        "route_error_ids": [row["id"] for row in rows if not bool(row["route_exact"])],
        "rows": rows,
    }


def _jh3_flow() -> dict[str, object]:
    suite = load_joint_retrieval_holdout_v3(JH3)
    rows = []
    for case in suite.cases:
        decision = route_question(case.question)
        plan = plan_knowledge_retrieval(case.question, decision=decision)
        expected_scopes = {scope.value for scope in case.expected_scopes}
        expected_temporal = {status.value for status in case.expected_temporal_statuses}
        predicted_scopes = {scope.value for scope in plan.scopes}
        predicted_temporal = {status.value for status in plan.temporal_statuses}
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
        "sha256": _sha256(JH3),
        "cases": len(rows),
        "route_exact": sum(bool(row["route_exact"]) for row in rows),
        "scope_exact": sum(bool(row["scope_exact"]) for row in rows),
        "temporal_exact": sum(bool(row["temporal_exact"]) for row in rows),
        "joint_exact": sum(bool(row["joint_exact"]) for row in rows),
        "route_error_ids": [row["id"] for row in rows if not bool(row["route_exact"])],
        "joint_error_ids": [row["id"] for row in rows if not bool(row["joint_exact"])],
        "rows": rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Avalia Router 1.4.0 apenas em conjuntos já conhecidos, mantendo Planner 1.2.0 "
            "congelado. Não produz nova evidência de generalização."
        )
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    jh3_manifest = json.loads(JH3_MANIFEST.read_text(encoding="utf-8"))
    attribution = json.loads(JH3_ATTRIBUTION.read_text(encoding="utf-8"))
    frozen_planner = jh3_manifest["frozen_flow"]
    current_planner_blob = _git_blob_sha(PLANNER_SOURCE)
    if RETRIEVAL_PLANNER_VERSION != "1.2.0":
        raise ValueError("Router 1.4 exige Planner 1.2.0 congelado")
    if RETRIEVAL_PLANNER_VERSION != frozen_planner["retrieval_planner_version"]:
        raise ValueError("Versão do Planner divergiu do fluxo medido no JH3")
    if current_planner_blob != frozen_planner["retrieval_planner_source_git_blob_sha"]:
        raise ValueError("Blob do Planner mudou durante tuning exclusivo do Router")

    jh3 = _jh3_flow()
    payload = {
        "artifact": "router_v1_4_known_regression",
        "status": "KNOWN_REGRESSION_ONLY",
        "router_version": ROUTER_VERSION,
        "router_source_git_blob_sha": _git_blob_sha(ROUTER_SOURCE),
        "planner_version_held_fixed": RETRIEVAL_PLANNER_VERSION,
        "planner_source_git_blob_sha": current_planner_blob,
        "routing_sets": {
            "development": _routing_result(DEVELOPMENT),
            "router_holdout_v1": _routing_result(ROUTER_HOLDOUT_V1),
            "router_holdout_v2": _routing_result(ROUTER_HOLDOUT_V2),
        },
        "joint_holdout_v2_route_regression": _jh2_routes(),
        "joint_holdout_v3_known_regression": jh3,
        "frozen_jh3_independent_baseline": {
            "route_exact": jh3_manifest["measurement"]["result"]["summary"]["route_exact"],
            "joint_exact": jh3_manifest["measurement"]["result"]["summary"]["joint_exact"],
            "joint_exact_rate": jh3_manifest["measurement"]["result"]["summary"][
                "joint_exact_rate"
            ],
        },
        "frozen_jh3_post_hoc_diagnostic": {
            "router_only_failures": attribution["results"]["router_only_failures"],
            "planner_only_failures": attribution["results"]["planner_only_failures"],
            "shared_failures": attribution["results"]["shared_router_planner_failures"],
            "router_contribution": attribution["results"][
                "router_contribution_to_joint_failures"
            ],
            "route_only_counterfactual_joint_exact": attribution["results"][
                "best_case_joint_exact_with_expected_route_correction_only"
            ],
        },
        "governance": {
            "all_evaluation_sets_known_before_router_1_4_tuning": True,
            "jh3_is_known_regression": True,
            "planner_modified_in_increment": False,
            "planner_blob_preserved": True,
            "historical_independent_measurement_preserved": True,
            "historical_post_hoc_diagnostic_preserved": True,
            "case_id_specific_rules_allowed": False,
            "new_generalization_claim": False,
            "llm_called": False,
            "sql_executed": False,
            "retriever_called": False,
            "external_embeddings_called": False,
        },
    }

    text = json.dumps(payload, ensure_ascii=False, indent=2)
    print(text)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
