from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from cpgf.ai import plan_knowledge_retrieval, route_question
from cpgf.benchmark import (
    evaluate_routing,
    load_benchmark,
    load_joint_retrieval_holdout,
)
from cpgf.version import RETRIEVAL_PLANNER_VERSION, ROUTER_VERSION

DEFAULT_DEVELOPMENT = Path("data/benchmarks/assistant_v1_0_0.csv")
DEFAULT_ROUTER_HOLDOUT_V1 = Path("data/benchmarks/assistant_router_holdout_v1_0_0.csv")
DEFAULT_ROUTER_HOLDOUT_V2 = Path("data/benchmarks/assistant_router_holdout_v2_0_0.csv")
DEFAULT_JOINT_HOLDOUT = Path("data/benchmarks/joint_retrieval_holdout_v2_0_0.csv")
DEFAULT_JOINT_MANIFEST = Path("data/manifests/joint_retrieval_holdout_2_0_0.json")
DEFAULT_DIAGNOSTIC_MANIFEST = Path(
    "data/manifests/joint_retrieval_flow_attribution_1_0_0.json"
)
PLANNER_SOURCE = Path("src/cpgf/ai/retrieval_planner.py")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git_blob_sha(path: Path) -> str:
    content = path.read_bytes()
    header = f"blob {len(content)}\0".encode()
    return hashlib.sha1(header + content).hexdigest()


def _routing_result(path: Path) -> dict[str, object]:
    result = evaluate_routing(load_benchmark(path))
    return {
        "path": str(path),
        "sha256": _sha256(path),
        "summary": result["summary"],
        "errors": [row for row in result["cases"] if not bool(row["exact"])],
    }


def _joint_known_regression(path: Path) -> dict[str, object]:
    suite = load_joint_retrieval_holdout(path)
    rows: list[dict[str, object]] = []
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
        rows.append(
            {
                "id": case.id,
                "category": case.category.value,
                "expected_route": case.expected_route.value,
                "predicted_route": decision.route.value,
                "route_exact": route_exact,
                "scope_exact": scope_exact,
                "temporal_exact": temporal_exact,
                "filter_joint_exact": scope_exact and temporal_exact,
                "joint_exact": route_exact and scope_exact and temporal_exact,
            }
        )

    return {
        "path": str(path),
        "sha256": _sha256(path),
        "cases": len(rows),
        "route_exact": sum(bool(row["route_exact"]) for row in rows),
        "filter_joint_exact": sum(bool(row["filter_joint_exact"]) for row in rows),
        "joint_exact": sum(bool(row["joint_exact"]) for row in rows),
        "route_error_ids": [row["id"] for row in rows if not bool(row["route_exact"])],
        "filter_error_ids": [
            row["id"] for row in rows if not bool(row["filter_joint_exact"])
        ],
        "joint_error_ids": [row["id"] for row in rows if not bool(row["joint_exact"])],
        "rows": rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Avalia Router 1.3.0 somente em conjuntos conhecidos, mantendo o Planner 1.1.0 "
            "congelado. Não produz nova alegação de generalização."
        )
    )
    parser.add_argument("--development", type=Path, default=DEFAULT_DEVELOPMENT)
    parser.add_argument("--router-holdout-v1", type=Path, default=DEFAULT_ROUTER_HOLDOUT_V1)
    parser.add_argument("--router-holdout-v2", type=Path, default=DEFAULT_ROUTER_HOLDOUT_V2)
    parser.add_argument("--joint-holdout", type=Path, default=DEFAULT_JOINT_HOLDOUT)
    parser.add_argument("--joint-manifest", type=Path, default=DEFAULT_JOINT_MANIFEST)
    parser.add_argument(
        "--diagnostic-manifest", type=Path, default=DEFAULT_DIAGNOSTIC_MANIFEST
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    joint_manifest = json.loads(args.joint_manifest.read_text(encoding="utf-8"))
    diagnostic_manifest = json.loads(
        args.diagnostic_manifest.read_text(encoding="utf-8")
    )
    frozen_planner_blob = joint_manifest["frozen_flow"][
        "retrieval_planner_source_git_blob_sha"
    ]
    current_planner_blob = _git_blob_sha(PLANNER_SOURCE)
    if RETRIEVAL_PLANNER_VERSION != "1.1.0":
        raise ValueError("Router 1.3.0 exige Planner 1.1.0 congelado")
    if current_planner_blob != frozen_planner_blob:
        raise ValueError("Planner divergiu do blob congelado da primeira medição do JH2")

    payload: dict[str, object] = {
        "artifact": "router_v1_3_known_regression",
        "router_version": ROUTER_VERSION,
        "planner_version_held_fixed": RETRIEVAL_PLANNER_VERSION,
        "planner_source_git_blob_sha": current_planner_blob,
        "status": "KNOWN_REGRESSION_ONLY",
        "routing_sets": {
            "development": _routing_result(args.development),
            "router_holdout_v1": _routing_result(args.router_holdout_v1),
            "router_holdout_v2": _routing_result(args.router_holdout_v2),
        },
        "joint_holdout_v2_known_regression": _joint_known_regression(args.joint_holdout),
        "frozen_independent_baseline": {
            "first_measurement_joint_exact": joint_manifest["measurement"]
            ["first_valid_measurement_result"]["joint_exact"],
            "first_measurement_route_exact": joint_manifest["measurement"]
            ["first_valid_measurement_result"]["route_exact"],
            "diagnostic_router_only_failures": diagnostic_manifest["results"][
                "router_only_failures"
            ],
            "diagnostic_planner_only_failures": diagnostic_manifest["results"][
                "planner_only_failures"
            ],
            "diagnostic_shared_failures": diagnostic_manifest["results"][
                "shared_router_planner_failures"
            ],
            "route_only_counterfactual_joint_exact": diagnostic_manifest["results"][
                "best_case_joint_exact_with_expected_route_correction_only"
            ],
            "historical_evidence_recomputed_with_router_v1_3": False,
        },
        "governance": {
            "all_evaluation_sets_known_before_router_v1_3_tuning": True,
            "joint_holdout_v2_is_regression_after_first_measurement": True,
            "new_generalization_claim": False,
            "planner_modified": False,
            "llm_called": False,
            "sql_executed": False,
            "retriever_called": False,
            "external_embeddings_called": False,
            "next_generalization_gate": (
                "Joint Holdout 3.0 independente depois de Router 1.3.0 e Planner 1.2.0"
            ),
        },
    }

    text = json.dumps(payload, ensure_ascii=False, indent=2)
    print(text)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
