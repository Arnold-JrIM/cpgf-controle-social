from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from cpgf.benchmark.joint_retrieval_v5 import (
    joint_holdout_v5_sha256,
    load_joint_retrieval_holdout_v5,
    prior_question_benchmark_paths,
    validate_joint_holdout_v5_against_catalog,
    validate_joint_holdout_v5_novelty,
)
from cpgf.version import (
    JOINT_RETRIEVAL_HOLDOUT_V5_VERSION,
    RETRIEVAL_PLANNER_VERSION,
    ROUTER_VERSION,
    SEMANTIC_CANDIDATE_VERSION,
)

BENCHMARK = Path("data/benchmarks/joint_retrieval_holdout_v5_0_0.csv")
BENCHMARK_DIR = Path("data/benchmarks")
MANIFEST = Path("data/manifests/joint_retrieval_holdout_5_0_0.json")
CANDIDATE_MANIFEST = Path("data/manifests/semantic_candidate_b_1_0_0.json")
CATALOG = Path("data/knowledge/source_catalog.json")
PROVIDER_SOURCE = Path("src/cpgf/ai/semantic_experiment.py")
PLANNER_SOURCE = Path("src/cpgf/ai/retrieval_planner.py")
ROUTER_SOURCE = Path("src/cpgf/ai/router.py")


def _git_blob_sha(path: Path) -> str:
    content = path.read_bytes()
    return hashlib.sha1(f"blob {len(content)}\0".encode() + content).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Valida estrutura, novidade e freeze prospectivo do JH5 sem executar "
            "candidata LLM, Router, Planner ou Retriever."
        )
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if manifest["status"] != "FROZEN_BEFORE_MEASUREMENT":
        raise ValueError(f"Estado inválido do JH5 antes da primeira medição: {manifest['status']}")
    if JOINT_RETRIEVAL_HOLDOUT_V5_VERSION != "5.0.0":
        raise ValueError("Versão JH5 inesperada")

    actual_benchmark_sha = joint_holdout_v5_sha256(BENCHMARK)
    if actual_benchmark_sha != manifest["benchmark"]["sha256"]:
        raise ValueError(f"Benchmark JH5 divergiu do manifesto: {actual_benchmark_sha}")

    suite = load_joint_retrieval_holdout_v5(BENCHMARK)
    catalog = validate_joint_holdout_v5_against_catalog(suite, CATALOG)
    prior_paths = prior_question_benchmark_paths(
        BENCHMARK_DIR,
        current_path=BENCHMARK,
    )
    novelty = validate_joint_holdout_v5_novelty(
        suite,
        prior_paths,
        max_similarity_allowed=manifest["novelty"]["prospective_max_similarity"],
    )
    if novelty["prior_questions_compared"] != manifest["novelty"]["prior_questions_expected"]:
        raise ValueError(
            "Universo histórico inesperado: "
            f"{novelty['prior_questions_compared']} perguntas"
        )

    candidate = manifest["candidate_freeze"]
    current_candidate_manifest_blob = _git_blob_sha(CANDIDATE_MANIFEST)
    current_provider_blob = _git_blob_sha(PROVIDER_SOURCE)
    current_planner_blob = _git_blob_sha(PLANNER_SOURCE)
    current_router_blob = _git_blob_sha(ROUTER_SOURCE)
    candidate_matches_freeze = (
        SEMANTIC_CANDIDATE_VERSION == candidate["candidate_version"]
        and RETRIEVAL_PLANNER_VERSION == candidate["retrieval_planner_version"]
        and ROUTER_VERSION == candidate["route_type_dependency_router_version"]
        and current_candidate_manifest_blob == candidate["manifest_git_blob_sha"]
        and current_provider_blob == candidate["provider_source_git_blob_sha"]
        and current_planner_blob == candidate["retrieval_planner_source_git_blob_sha"]
        and current_router_blob == candidate["route_type_dependency_router_blob_sha"]
    )
    if not candidate_matches_freeze:
        raise ValueError("Candidata B ou dependências mudaram após início da autoria do JH5")

    criteria = manifest["prospective_acceptance_gate"]
    if not criteria["defined_before_first_measurement"]:
        raise ValueError("Gate JH5 não foi definido prospectivamente")
    if criteria["performance_threshold_causes_measurement_workflow_failure"]:
        raise ValueError("O desempenho não pode apagar a primeira medição independente")

    governance = manifest["governance"]
    if not governance["benchmark_authored_without_candidate_outputs"]:
        raise ValueError("JH5 exige autoria sem saídas da candidata")
    if not governance["candidate_specification_frozen_before_benchmark_authoring"]:
        raise ValueError("Candidata deve ter sido congelada antes da autoria")

    payload = {
        "artifact": "joint_retrieval_holdout_v5_preflight",
        "status": "PASS",
        "manifest_status": manifest["status"],
        "benchmark_sha256": actual_benchmark_sha,
        "catalog_validation": catalog,
        "novelty_validation": novelty,
        "candidate_freeze": candidate,
        "current_candidate": {
            "candidate_version": SEMANTIC_CANDIDATE_VERSION,
            "candidate_manifest_git_blob_sha": current_candidate_manifest_blob,
            "provider_source_git_blob_sha": current_provider_blob,
            "retrieval_planner_version": RETRIEVAL_PLANNER_VERSION,
            "retrieval_planner_source_git_blob_sha": current_planner_blob,
            "router_version": ROUTER_VERSION,
            "router_source_git_blob_sha": current_router_blob,
            "matches_frozen_candidate": candidate_matches_freeze,
        },
        "prospective_acceptance_gate": criteria,
        "governance": {
            "candidate_llm_called": False,
            "deterministic_router_called": False,
            "retrieval_planner_called": False,
            "retriever_called": False,
            "sql_executed": False,
            "external_embeddings_called": False,
            "measurement_performed": False,
            "candidate_outputs_used_during_authoring": False,
            "first_measurement_requires_freeze_merged": True,
        },
    }
    args.output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
