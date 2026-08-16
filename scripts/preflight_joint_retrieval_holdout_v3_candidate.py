from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from cpgf.benchmark.joint_retrieval_v3 import (
    joint_holdout_v3_sha256,
    load_joint_retrieval_holdout_v3,
    validate_joint_holdout_v3_against_catalog,
    validate_joint_holdout_v3_novelty,
)
from cpgf.version import KNOWLEDGE_VERSION, RETRIEVAL_PLANNER_VERSION, ROUTER_VERSION

DEFAULT_HOLDOUT = Path("data/benchmarks/joint_retrieval_holdout_v3_0_0.csv")
DEFAULT_CATALOG = Path("data/knowledge/source_catalog.json")
DEFAULT_PRIOR = (
    Path("data/benchmarks/knowledge_retrieval_v1_0_0.csv"),
    Path("data/benchmarks/retrieval_planner_holdout_v1_0_0.csv"),
    Path("data/benchmarks/assistant_v1_0_0.csv"),
    Path("data/benchmarks/assistant_router_holdout_v1_0_0.csv"),
    Path("data/benchmarks/assistant_router_holdout_v2_0_0.csv"),
    Path("data/benchmarks/joint_retrieval_holdout_v2_0_0.csv"),
)
ROUTER_SOURCE = Path("src/cpgf/ai/router.py")
PLANNER_SOURCE = Path("src/cpgf/ai/retrieval_planner.py")
EXPECTED_ROUTER_BLOB = "7c82b42f4409110371dcb86e15672a328a0d54bd"
EXPECTED_PLANNER_BLOB = "7ee30359cb4457b0bd1a12b43d14f73be410ddaa"


def _git_blob_sha(path: Path) -> str:
    content = path.read_bytes()
    header = f"blob {len(content)}\0".encode()
    return hashlib.sha1(header + content).hexdigest()


def _write(payload: dict[str, object], output: Path | None) -> None:
    text = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)
    print(text)
    if output:
        output.write_text(text + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Valida o candidato do Joint Holdout 3.0 antes do freeze. "
            "Não executa Router, Planner, Retriever, LLM ou embeddings."
        )
    )
    parser.add_argument("--holdout", type=Path, default=DEFAULT_HOLDOUT)
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    try:
        if ROUTER_VERSION != "1.3.0":
            raise ValueError(f"Router corrente inesperado: {ROUTER_VERSION}")
        if RETRIEVAL_PLANNER_VERSION != "1.2.0":
            raise ValueError(f"Planner corrente inesperado: {RETRIEVAL_PLANNER_VERSION}")
        if KNOWLEDGE_VERSION != "1.2.0":
            raise ValueError(f"Knowledge corrente inesperado: {KNOWLEDGE_VERSION}")

        router_blob = _git_blob_sha(ROUTER_SOURCE)
        planner_blob = _git_blob_sha(PLANNER_SOURCE)
        if router_blob != EXPECTED_ROUTER_BLOB:
            raise ValueError(f"Router divergiu antes do freeze: {router_blob}")
        if planner_blob != EXPECTED_PLANNER_BLOB:
            raise ValueError(f"Planner divergiu antes do freeze: {planner_blob}")

        suite = load_joint_retrieval_holdout_v3(args.holdout)
        catalog = validate_joint_holdout_v3_against_catalog(suite, args.catalog)
        novelty = validate_joint_holdout_v3_novelty(
            suite,
            DEFAULT_PRIOR,
            max_similarity_allowed=0.80,
        )
        if novelty["prior_questions_compared"] != 230:
            raise ValueError(
                "Universo prévio inesperado: "
                f"{novelty['prior_questions_compared']} != 230"
            )

        payload: dict[str, object] = {
            "artifact": "joint_retrieval_holdout_v3_candidate_preflight",
            "version": suite.version,
            "status": "PASS",
            "candidate_sha256": joint_holdout_v3_sha256(args.holdout),
            "frozen_flow_candidate": {
                "router_version": ROUTER_VERSION,
                "router_source_git_blob_sha": router_blob,
                "retrieval_planner_version": RETRIEVAL_PLANNER_VERSION,
                "retrieval_planner_source_git_blob_sha": planner_blob,
                "knowledge_version": KNOWLEDGE_VERSION,
            },
            "catalog_validation": catalog,
            "novelty_validation": novelty,
            "governance": {
                "candidate_not_frozen_yet": True,
                "questions_may_change_only_before_freeze": True,
                "prospective_similarity_threshold": 0.80,
                "prior_questions_compared_expected": 230,
                "router_called": False,
                "retrieval_planner_called": False,
                "retriever_called": False,
                "llm_called": False,
                "sql_executed": False,
                "external_embeddings_called": False,
                "measurement_performed": False,
            },
        }
        _write(payload, args.output)
    except Exception as exc:
        failure = {
            "artifact": "joint_retrieval_holdout_v3_candidate_preflight",
            "status": "FAIL",
            "candidate_sha256": (
                joint_holdout_v3_sha256(args.holdout) if args.holdout.exists() else None
            ),
            "error_type": type(exc).__name__,
            "error": str(exc),
            "governance": {
                "candidate_not_frozen_yet": True,
                "router_called": False,
                "retrieval_planner_called": False,
                "retriever_called": False,
                "llm_called": False,
                "measurement_performed": False,
            },
        }
        _write(failure, args.output)
        raise


if __name__ == "__main__":
    main()
