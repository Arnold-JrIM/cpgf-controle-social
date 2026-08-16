from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from cpgf.benchmark.joint_retrieval_v4 import (
    joint_holdout_v4_sha256,
    load_joint_retrieval_holdout_v4,
    validate_joint_holdout_v4_against_catalog,
    validate_joint_holdout_v4_novelty,
)
from cpgf.version import (
    JOINT_RETRIEVAL_HOLDOUT_V4_VERSION,
    KNOWLEDGE_VERSION,
    RETRIEVAL_PLANNER_VERSION,
    ROUTER_VERSION,
)

BENCHMARK = Path("data/benchmarks/joint_retrieval_holdout_v4_0_0.csv")
MANIFEST = Path("data/manifests/joint_retrieval_holdout_4_0_0.json")
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
ROUTER_SOURCE = Path("src/cpgf/ai/router.py")
PLANNER_SOURCE = Path("src/cpgf/ai/retrieval_planner.py")
_ALLOWED_STATES = {"FROZEN_BEFORE_MEASUREMENT", "MEASURED_INDEPENDENT"}


def _git_blob_sha(path: Path) -> str:
    content = path.read_bytes()
    return hashlib.sha1(f"blob {len(content)}\0".encode() + content).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Valida estrutura, novidade e freeze do JH4 sem executar Router, Planner, "
            "Retriever ou LLM."
        )
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if manifest["status"] not in _ALLOWED_STATES:
        raise ValueError(f"Estado inválido do JH4: {manifest['status']}")
    if JOINT_RETRIEVAL_HOLDOUT_V4_VERSION != "4.0.0":
        raise ValueError("Versão JH4 inesperada")

    actual_sha = joint_holdout_v4_sha256(BENCHMARK)
    expected_sha = manifest["benchmark"]["sha256"]
    if actual_sha != expected_sha:
        raise ValueError(f"Benchmark JH4 mudou após freeze: {actual_sha}")

    suite = load_joint_retrieval_holdout_v4(BENCHMARK)
    catalog = validate_joint_holdout_v4_against_catalog(suite, CATALOG)
    novelty = validate_joint_holdout_v4_novelty(
        suite,
        PRIOR,
        max_similarity_allowed=manifest["novelty"]["prospective_max_similarity"],
    )

    frozen = manifest["frozen_flow"]
    current_router_blob = _git_blob_sha(ROUTER_SOURCE)
    current_planner_blob = _git_blob_sha(PLANNER_SOURCE)
    current_flow_matches_frozen = (
        ROUTER_VERSION == frozen["router_version"]
        and RETRIEVAL_PLANNER_VERSION == frozen["retrieval_planner_version"]
        and KNOWLEDGE_VERSION == frozen["knowledge_version"]
        and current_router_blob == frozen["router_source_git_blob_sha"]
        and current_planner_blob == frozen["retrieval_planner_source_git_blob_sha"]
    )

    if manifest["status"] == "FROZEN_BEFORE_MEASUREMENT" and not current_flow_matches_frozen:
        raise ValueError("Fluxo corrente divergiu do freeze antes da primeira medição do JH4")

    if manifest["status"] == "MEASURED_INDEPENDENT":
        first = manifest["measurement"]["first_valid_measurement"]
        if not first or not first.get("run_id") or not first.get("head_sha"):
            raise ValueError("JH4 marcado como medido sem referência da primeira medição")

    criteria = manifest["prospective_success_criteria"]
    if not criteria["defined_before_first_measurement"]:
        raise ValueError("Critérios prospectivos não foram congelados antes da medição")
    if criteria["performance_threshold_causes_measurement_workflow_failure"]:
        raise ValueError("Desempenho não pode apagar ou invalidar a primeira medição")

    payload = {
        "artifact": "joint_retrieval_holdout_v4_preflight",
        "status": "PASS",
        "manifest_status": manifest["status"],
        "benchmark_sha256": actual_sha,
        "catalog_validation": catalog,
        "novelty_validation": novelty,
        "frozen_flow": frozen,
        "current_flow": {
            "router_version": ROUTER_VERSION,
            "router_source_git_blob_sha": current_router_blob,
            "retrieval_planner_version": RETRIEVAL_PLANNER_VERSION,
            "retrieval_planner_source_git_blob_sha": current_planner_blob,
            "knowledge_version": KNOWLEDGE_VERSION,
            "matches_frozen_flow": current_flow_matches_frozen,
        },
        "prospective_success_criteria": criteria,
        "governance": {
            "router_called": False,
            "retrieval_planner_called": False,
            "retriever_called": False,
            "llm_called": False,
            "sql_executed": False,
            "external_embeddings_called": False,
            "measurement_performed": False,
            "pre_measurement_requires_current_flow_match": True,
            "post_measurement_allows_operational_versions_to_advance": True,
            "historical_frozen_flow_preserved_from_manifest": True,
        },
    }
    args.output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
