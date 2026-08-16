from __future__ import annotations

import argparse
import json
from pathlib import Path

from cpgf.ai import plan_knowledge_retrieval
from cpgf.benchmark import benchmark_sha256, evaluate_retrieval_planner, load_retrieval_benchmark
from cpgf.version import RETRIEVAL_PLANNER_VERSION, ROUTER_VERSION

DEVELOPMENT = Path("data/benchmarks/knowledge_retrieval_v1_0_0.csv")
KNOWN_HOLDOUT = Path("data/benchmarks/retrieval_planner_holdout_v1_0_0.csv")


def _evaluate(path: Path) -> dict[str, object]:
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


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Avalia o Retrieval Planner 1.1.0 somente em conjuntos já conhecidos."
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    payload = {
        "artifact": "retrieval_planner_1_1_regression",
        "status": "KNOWN_REGRESSION_ONLY",
        "router_version": ROUTER_VERSION,
        "planner_version": RETRIEVAL_PLANNER_VERSION,
        "development": _evaluate(DEVELOPMENT),
        "known_holdout": _evaluate(KNOWN_HOLDOUT),
        "governance": {
            "new_generalization_claim": False,
            "development_set_already_known": True,
            "holdout_set_already_known_after_prior_measurement": True,
            "llm_called": False,
            "sql_executed": False,
        },
    }
    args.output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
