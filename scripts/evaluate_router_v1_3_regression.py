from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from cpgf.ai import route_question
from cpgf.benchmark import evaluate_routing, load_benchmark, load_joint_retrieval_holdout
from cpgf.version import RETRIEVAL_PLANNER_VERSION, ROUTER_VERSION

DEFAULT_DEVELOPMENT = Path("data/benchmarks/assistant_v1_0_0.csv")
DEFAULT_ROUTER_HOLDOUT_V1 = Path("data/benchmarks/assistant_router_holdout_v1_0_0.csv")
DEFAULT_ROUTER_HOLDOUT_V2 = Path("data/benchmarks/assistant_router_holdout_v2_0_0.csv")
DEFAULT_JOINT_HOLDOUT = Path("data/benchmarks/joint_retrieval_holdout_v2_0_0.csv")
DEFAULT_ROUTER_MANIFEST = Path("data/manifests/assistant_router_1_3_0.json")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _routing_result(path: Path) -> dict[str, object]:
    result = evaluate_routing(load_benchmark(path))
    return {
        "path": str(path),
        "sha256": _sha256(path),
        "summary": result["summary"],
        "errors": [row for row in result["cases"] if not bool(row["exact"])],
    }


def _joint_route_regression(path: Path) -> dict[str, object]:
    suite = load_joint_retrieval_holdout(path)
    rows: list[dict[str, object]] = []
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
        "path": str(path),
        "sha256": _sha256(path),
        "cases": len(rows),
        "route_exact": sum(bool(row["route_exact"]) for row in rows),
        "route_error_ids": [row["id"] for row in rows if not bool(row["route_exact"])],
        "rows": rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Preserva a evidência histórica do Router 1.3 e verifica se o Router corrente "
            "continua compatível com seus conjuntos de regressão conhecidos."
        )
    )
    parser.add_argument("--development", type=Path, default=DEFAULT_DEVELOPMENT)
    parser.add_argument("--router-holdout-v1", type=Path, default=DEFAULT_ROUTER_HOLDOUT_V1)
    parser.add_argument("--router-holdout-v2", type=Path, default=DEFAULT_ROUTER_HOLDOUT_V2)
    parser.add_argument("--joint-holdout", type=Path, default=DEFAULT_JOINT_HOLDOUT)
    parser.add_argument("--router-manifest", type=Path, default=DEFAULT_ROUTER_MANIFEST)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    router_manifest = json.loads(args.router_manifest.read_text(encoding="utf-8"))
    historical_joint = router_manifest["known_regression_sets"]["joint_holdout_v2"]
    history = router_manifest["historical_independent_evidence"]

    payload: dict[str, object] = {
        "artifact": "router_v1_3_historical_evidence_with_current_regression",
        "status": "HISTORICAL_EVIDENCE_WITH_CURRENT_ROUTER_REGRESSION",
        "historical_router_version": router_manifest["router_version"],
        "historical_router_source_git_blob_sha": router_manifest[
            "router_source_git_blob_sha"
        ],
        "current_router_version": ROUTER_VERSION,
        "current_planner_version": RETRIEVAL_PLANNER_VERSION,
        "historical_planner_version_held_fixed": router_manifest[
            "planner_version_held_fixed"
        ],
        "routing_sets": {
            "development": _routing_result(args.development),
            "router_holdout_v1": _routing_result(args.router_holdout_v1),
            "router_holdout_v2": _routing_result(args.router_holdout_v2),
        },
        "joint_holdout_v2_route_regression": _joint_route_regression(args.joint_holdout),
        "historical_joint_holdout_v2_with_planner_1_1": historical_joint,
        "frozen_independent_baseline": {
            "first_measurement_joint_exact": history["joint_holdout_v2_first_measurement"][
                "joint_exact"
            ],
            "first_measurement_route_exact": history[
                "joint_holdout_v2_first_measurement"
            ]["route_exact"],
            "diagnostic_router_only_failures": history["post_hoc_diagnostic_v1"][
                "router_only_failures"
            ],
            "diagnostic_planner_only_failures": history["post_hoc_diagnostic_v1"][
                "planner_only_failures"
            ],
            "diagnostic_shared_failures": history["post_hoc_diagnostic_v1"][
                "shared_router_planner_failures"
            ],
            "route_only_counterfactual_joint_exact": history["post_hoc_diagnostic_v1"][
                "route_only_counterfactual_joint_exact"
            ],
        },
        "governance": {
            "current_router_regression_recomputed": True,
            "historical_router_blob_preserved_from_manifest": True,
            "historical_joint_filters_recomputed_with_current_planner": False,
            "current_router_may_advance": True,
            "current_planner_may_advance": True,
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
