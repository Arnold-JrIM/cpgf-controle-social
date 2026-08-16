from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from cpgf.benchmark import evaluate_routing, load_benchmark
from cpgf.version import ROUTER_VERSION

DEFAULT_DEVELOPMENT = Path("data/benchmarks/assistant_v1_0_0.csv")
DEFAULT_ROUTER_HOLDOUT_V1 = Path("data/benchmarks/assistant_router_holdout_v1_0_0.csv")
DEFAULT_ROUTER_HOLDOUT_V2 = Path("data/benchmarks/assistant_router_holdout_v2_0_0.csv")
DEFAULT_FROZEN_MANIFEST = Path("data/manifests/assistant_router_1_2_0.json")


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


def _historical_retrieval_baseline(path: Path) -> dict[str, object]:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    historical = manifest["known_regression_sets"]["retrieval_planner_holdout_v1"]
    return {
        "manifest_path": str(path),
        "router_version": manifest["router_version"],
        "planner_version_held_fixed": manifest["planner_version_held_fixed"],
        "path": historical["path"],
        "sha256": historical["sha256"],
        "cases": historical["cases"],
        "joint_exact": historical["joint_exact"],
        "joint_filter_failures": historical["joint_filter_failures"],
        "router_contribution_to_joint_failures": historical[
            "router_contribution_to_joint_failures"
        ],
        "planner_contribution_to_joint_failures": historical[
            "planner_contribution_to_joint_failures"
        ],
        "latent_router_issues_with_exact_filters": historical[
            "latent_router_issues_with_exact_filters"
        ],
        "attribution_counts": historical["attribution_counts"],
        "planner_failure_ids": historical["planner_failure_ids"],
        "frozen_historical_evidence": True,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Avalia Router 1.2.0 nos conjuntos de roteamento conhecidos e preserva "
            "separadamente a linha de base documental histórica medida com Planner 1.0.0."
        )
    )
    parser.add_argument("--development", type=Path, default=DEFAULT_DEVELOPMENT)
    parser.add_argument("--router-holdout-v1", type=Path, default=DEFAULT_ROUTER_HOLDOUT_V1)
    parser.add_argument("--router-holdout-v2", type=Path, default=DEFAULT_ROUTER_HOLDOUT_V2)
    parser.add_argument("--frozen-manifest", type=Path, default=DEFAULT_FROZEN_MANIFEST)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    payload: dict[str, object] = {
        "artifact": "router_regression_evaluation",
        "router_version": ROUTER_VERSION,
        "status": "KNOWN_REGRESSION_ONLY",
        "routing_sets": {
            "development": _routing_result(args.development),
            "router_holdout_v1": _routing_result(args.router_holdout_v1),
            "router_holdout_v2": _routing_result(args.router_holdout_v2),
        },
        "historical_retrieval_flow": _historical_retrieval_baseline(args.frozen_manifest),
        "governance": {
            "all_router_evaluation_sets_known_before_router_v1_2": True,
            "new_generalization_claim": False,
            "historical_retrieval_flow_recomputed_with_current_planner": False,
            "router_regression_decoupled_from_current_planner": True,
            "llm_called": False,
            "sql_executed": False,
            "next_generalization_gate": (
                "novo holdout conjunto independente apos Router 1.2.0 e Planner 1.1.0"
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
