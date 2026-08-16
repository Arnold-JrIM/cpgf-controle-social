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
from cpgf.version import (
    JOINT_RETRIEVAL_HOLDOUT_V3_VERSION,
    KNOWLEDGE_VERSION,
    RETRIEVAL_PLANNER_VERSION,
    ROUTER_VERSION,
)

BENCHMARK = Path("data/benchmarks/joint_retrieval_holdout_v3_0_0.csv")
MANIFEST = Path("data/manifests/joint_retrieval_holdout_3_0_0.json")
CATALOG = Path("data/knowledge/source_catalog.json")
PRIOR = (
    Path("data/benchmarks/knowledge_retrieval_v1_0_0.csv"),
    Path("data/benchmarks/retrieval_planner_holdout_v1_0_0.csv"),
    Path("data/benchmarks/assistant_v1_0_0.csv"),
    Path("data/benchmarks/assistant_router_holdout_v1_0_0.csv"),
    Path("data/benchmarks/assistant_router_holdout_v2_0_0.csv"),
    Path("data/benchmarks/joint_retrieval_holdout_v2_0_0.csv"),
)
ROUTER_SOURCE = Path("src/cpgf/ai/router.py")
PLANNER_SOURCE = Path("src/cpgf/ai/retrieval_planner.py")


def _git_blob_sha(path: Path) -> str:
    content = path.read_bytes()
    return hashlib.sha1(f"blob {len(content)}\0".encode() + content).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description="Valida o JH3 congelado sem executar o fluxo.")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if manifest["status"] not in {"FROZEN_BEFORE_MEASUREMENT", "MEASURED_INDEPENDENT"}:
        raise ValueError(f"Estado inválido: {manifest['status']}")
    if JOINT_RETRIEVAL_HOLDOUT_V3_VERSION != "3.0.0":
        raise ValueError("Versão JH3 inesperada")

    expected_sha = manifest["benchmark"]["sha256"]
    actual_sha = joint_holdout_v3_sha256(BENCHMARK)
    if actual_sha != expected_sha:
        raise ValueError(f"Benchmark JH3 mudou após freeze: {actual_sha}")

    frozen = manifest["frozen_flow"]
    actual_router_blob = _git_blob_sha(ROUTER_SOURCE)
    actual_planner_blob = _git_blob_sha(PLANNER_SOURCE)
    if ROUTER_VERSION != frozen["router_version"] or actual_router_blob != frozen["router_source_git_blob_sha"]:
        raise ValueError("Router não corresponde ao fluxo congelado")
    if RETRIEVAL_PLANNER_VERSION != frozen["retrieval_planner_version"] or actual_planner_blob != frozen["retrieval_planner_source_git_blob_sha"]:
        raise ValueError("Planner não corresponde ao fluxo congelado")
    if KNOWLEDGE_VERSION != frozen["knowledge_version"]:
        raise ValueError("Knowledge não corresponde ao fluxo congelado")

    suite = load_joint_retrieval_holdout_v3(BENCHMARK)
    catalog = validate_joint_holdout_v3_against_catalog(suite, CATALOG)
    novelty = validate_joint_holdout_v3_novelty(suite, PRIOR, max_similarity_allowed=0.80)

    payload = {
        "artifact": "joint_retrieval_holdout_v3_preflight",
        "status": "PASS",
        "manifest_status": manifest["status"],
        "benchmark_sha256": actual_sha,
        "catalog_validation": catalog,
        "novelty_validation": novelty,
        "frozen_flow": {
            "router_version": ROUTER_VERSION,
            "router_source_git_blob_sha": actual_router_blob,
            "retrieval_planner_version": RETRIEVAL_PLANNER_VERSION,
            "retrieval_planner_source_git_blob_sha": actual_planner_blob,
            "knowledge_version": KNOWLEDGE_VERSION,
        },
        "governance": {
            "router_called": False,
            "retrieval_planner_called": False,
            "retriever_called": False,
            "llm_called": False,
            "sql_executed": False,
            "external_embeddings_called": False,
            "measurement_performed": False,
        },
    }
    text = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)
    print(text)
    if args.output:
        args.output.write_text(text + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
