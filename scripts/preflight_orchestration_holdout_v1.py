from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path

from cpgf.ai.model_policy import DEFAULT_LLM_MODEL, LLM_MODEL_POLICY_VERSION
from cpgf.ai.semantic_orchestrator import (
    SEMANTIC_ORCHESTRATOR_POLICY_VERSION,
    SEMANTIC_ORCHESTRATOR_VERSION,
)
from cpgf.benchmark.orchestration_holdout_v1 import (
    ORCHESTRATION_HOLDOUT_VERSION,
    load_orchestration_holdout,
    orchestration_holdout_sha256,
    prior_question_benchmark_paths,
    validate_orchestration_holdout_capabilities,
    validate_orchestration_holdout_novelty,
)
from cpgf.version import EVIDENCE_CONTRACT_VERSION

BENCHMARK = Path("data/benchmarks/orchestration_holdout_v1_0_0.csv.gz")
BENCHMARK_DIR = Path("data/benchmarks")
MANIFEST = Path("data/manifests/orchestration_holdout_1_0_0.json")
SOURCES = {
    "orchestrator_source_git_blob_sha": Path("src/cpgf/ai/semantic_orchestrator.py"),
    "model_policy_source_git_blob_sha": Path("src/cpgf/ai/model_policy.py"),
    "evidence_contract_source_git_blob_sha": Path("src/cpgf/ai/evidence_contracts.py"),
    "evidence_worker_source_git_blob_sha": Path("src/cpgf/ai/evidence_workers.py"),
    "tool_registry_source_git_blob_sha": Path("src/cpgf/ai/tools/registry.py"),
    "web_evidence_source_git_blob_sha": Path("src/cpgf/ai/web_evidence.py"),
}


def _git_blob_sha(path: Path) -> str:
    content = path.read_bytes()
    return hashlib.sha1(f"blob {len(content)}\0".encode() + content).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Valida o freeze prospectivo do Orchestration Holdout 1.0.0 sem chamar "
            "LLM, plan_evidence, workers, Retriever ou Web."
        )
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if manifest["status"] != "FROZEN_BEFORE_MEASUREMENT":
        raise ValueError("Estado inválido antes da primeira medição")
    if ORCHESTRATION_HOLDOUT_VERSION != "1.0.0":
        raise ValueError("Versão inesperada do Orchestration Holdout")

    actual_sha = orchestration_holdout_sha256(BENCHMARK)
    if actual_sha != manifest["benchmark"]["sha256"]:
        raise ValueError(f"Benchmark divergiu do manifesto: {actual_sha}")

    suite = load_orchestration_holdout(BENCHMARK)
    capabilities = validate_orchestration_holdout_capabilities(suite)
    prior_paths = prior_question_benchmark_paths(BENCHMARK_DIR, current_path=BENCHMARK)
    novelty = validate_orchestration_holdout_novelty(
        suite,
        prior_paths,
        max_similarity_allowed=manifest["novelty"]["prospective_max_similarity"],
    )
    if len(prior_paths) != manifest["novelty"]["prior_benchmarks_expected"]:
        raise ValueError(f"Universo histórico inesperado: {len(prior_paths)} benchmarks")
    if novelty["prior_questions_compared"] != manifest["novelty"]["prior_questions_expected"]:
        raise ValueError(
            f"Universo histórico inesperado: {novelty['prior_questions_compared']} perguntas"
        )

    frozen = manifest["candidate_freeze"]
    current_blobs = {name: _git_blob_sha(path) for name, path in SOURCES.items()}
    versions_match = (
        SEMANTIC_ORCHESTRATOR_VERSION == frozen["orchestrator_version"]
        and SEMANTIC_ORCHESTRATOR_POLICY_VERSION == frozen["orchestrator_policy_version"]
        and EVIDENCE_CONTRACT_VERSION == frozen["evidence_contract_version"]
        and LLM_MODEL_POLICY_VERSION == frozen["model_policy_version"]
        and DEFAULT_LLM_MODEL == frozen["model"]
        and importlib.metadata.version("openai") == frozen["openai_sdk_version"]
    )
    blobs_match = all(current_blobs[name] == frozen[name] for name in SOURCES)
    if not versions_match or not blobs_match:
        raise ValueError("Orchestrator ou dependências mudaram após início da autoria do holdout")

    gate = manifest["prospective_acceptance_gate"]
    if not gate["defined_before_first_measurement"]:
        raise ValueError("Gate não foi definido prospectivamente")
    if gate["performance_threshold_causes_measurement_workflow_failure"]:
        raise ValueError("O desempenho não pode apagar a primeira medição independente")

    governance = manifest["governance"]
    if not governance["benchmark_authored_without_candidate_outputs"]:
        raise ValueError("Holdout exige autoria sem saídas da candidata")
    if not governance["candidate_specification_frozen_before_benchmark_authoring"]:
        raise ValueError("Orchestrator deve estar congelado antes da autoria")

    payload = {
        "artifact": "orchestration_holdout_v1_preflight",
        "status": "PASS",
        "manifest_status": manifest["status"],
        "benchmark_sha256": actual_sha,
        "benchmark_uncompressed_sha256": manifest["benchmark"]["uncompressed_sha256"],
        "capability_validation": capabilities,
        "novelty_validation": novelty,
        "candidate_freeze": frozen,
        "current_candidate": {
            "orchestrator_version": SEMANTIC_ORCHESTRATOR_VERSION,
            "orchestrator_policy_version": SEMANTIC_ORCHESTRATOR_POLICY_VERSION,
            "evidence_contract_version": EVIDENCE_CONTRACT_VERSION,
            "model_policy_version": LLM_MODEL_POLICY_VERSION,
            "model": DEFAULT_LLM_MODEL,
            "openai_sdk_version": importlib.metadata.version("openai"),
            **current_blobs,
            "matches_frozen_candidate": versions_match and blobs_match,
        },
        "prospective_acceptance_gate": gate,
        "governance": {
            "llm_called": False,
            "plan_evidence_called": False,
            "workers_called": False,
            "retriever_called": False,
            "web_called": False,
            "sql_executed": False,
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
