from __future__ import annotations

import argparse
import json
from pathlib import Path

from cpgf.benchmark.joint_retrieval_v4 import (
    joint_holdout_v4_sha256,
    load_joint_retrieval_holdout_v4,
    validate_joint_holdout_v4_against_catalog,
    validate_joint_holdout_v4_novelty,
)

BENCHMARK = Path("data/benchmarks/joint_retrieval_holdout_v4_0_0.csv")
CATALOG = Path("data/knowledge/source_catalog.json")
PRIOR = (
    Path("data/benchmarks/knowledge_retrieval_v1_0_0.csv"),
    Path("data/benchmarks/retrieval_planner_holdout_v1_0_0.csv"),
    Path("data/benchmarks/assistant_v1_0_0.csv"),
    Path("data/benchmarks/assistant_router_holdout_v1_0_0.csv"),
    Path("data/benchmarks/assistant_router_holdout_v2_0_0.csv"),
    Path("data/benchmarks/joint_retrieval_holdout_v2_0_0.csv"),
    Path("data/benchmarks/joint_retrieval_holdout_v3_0_0.csv"),
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Valida somente estrutura, catálogo e novidade do candidato JH4. "
            "Não executa Router, Planner, Retriever ou LLM."
        )
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    suite = load_joint_retrieval_holdout_v4(BENCHMARK)
    catalog = validate_joint_holdout_v4_against_catalog(suite, CATALOG)
    novelty = validate_joint_holdout_v4_novelty(
        suite,
        PRIOR,
        max_similarity_allowed=0.75,
    )
    payload = {
        "artifact": "joint_retrieval_holdout_v4_candidate_preflight",
        "status": "PASS",
        "benchmark_sha256": joint_holdout_v4_sha256(BENCHMARK),
        "catalog_validation": catalog,
        "novelty_validation": novelty,
        "governance": {
            "candidate_only": True,
            "oracles_defined_before_model_execution": True,
            "router_called": False,
            "retrieval_planner_called": False,
            "retriever_called": False,
            "llm_called": False,
            "sql_executed": False,
            "external_embeddings_called": False,
            "measurement_performed": False,
        },
    }
    args.output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
