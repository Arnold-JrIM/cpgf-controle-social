from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from cpgf.benchmark import (
    evaluate_retrieval_flow_attribution,
    evaluate_routing,
    load_benchmark,
    load_retrieval_benchmark,
)
from cpgf.version import RETRIEVAL_PLANNER_VERSION, ROUTER_VERSION

DEFAULT_DEVELOPMENT = Path("data/benchmarks/assistant_v1_0_0.csv")
DEFAULT_ROUTER_HOLDOUT_V1 = Path("data/benchmarks/assistant_router_holdout_v1_0_0.csv")
DEFAULT_ROUTER_HOLDOUT_V2 = Path("data/benchmarks/assistant_router_holdout_v2_0_0.csv")
DEFAULT_RETRIEVAL_HOLDOUT = Path("data/benchmarks/retrieval_planner_holdout_v1_0_0.csv")


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


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Avalia Router 1.2.0 somente em conjuntos conhecidos de regressão."
    )
    parser.add_argument("--development", type=Path, default=DEFAULT_DEVELOPMENT)
    parser.add_argument("--router-holdout-v1", type=Path, default=DEFAULT_ROUTER_HOLDOUT_V1)
    parser.add_argument("--router-holdout-v2", type=Path, default=DEFAULT_ROUTER_HOLDOUT_V2)
    parser.add_argument("--retrieval-holdout", type=Path, default=DEFAULT_RETRIEVAL_HOLDOUT)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    retrieval_suite = load_retrieval_benchmark(args.retrieval_holdout)
    retrieval_flow = evaluate_retrieval_flow_attribution(retrieval_suite)

    payload: dict[str, object] = {
        "artifact": "router_regression_evaluation",
        "router_version": ROUTER_VERSION,
        "planner_version_held_fixed": RETRIEVAL_PLANNER_VERSION,
        "status": "KNOWN_REGRESSION_ONLY",
        "routing_sets": {
            "development": _routing_result(args.development),
            "router_holdout_v1": _routing_result(args.router_holdout_v1),
            "router_holdout_v2": _routing_result(args.router_holdout_v2),
        },
        "retrieval_flow": {
            "path": str(args.retrieval_holdout),
            "sha256": _sha256(args.retrieval_holdout),
            "cases": retrieval_flow["cases"],
            "joint_filter_failures": retrieval_flow["joint_filter_failures"],
            "clean_passes": retrieval_flow["clean_passes"],
            "router_contribution_to_joint_failures": retrieval_flow[
                "router_contribution_to_joint_failures"
            ],
            "planner_contribution_to_joint_failures": retrieval_flow[
                "planner_contribution_to_joint_failures"
            ],
            "latent_router_issues_with_exact_filters": retrieval_flow[
                "latent_router_issues_with_exact_filters"
            ],
            "attribution_counts": retrieval_flow["attribution_counts"],
            "ids_by_attribution": retrieval_flow["ids_by_attribution"],
        },
        "governance": {
            "all_evaluation_sets_known_before_router_v1_2": True,
            "new_generalization_claim": False,
            "planner_modified_in_increment": False,
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
