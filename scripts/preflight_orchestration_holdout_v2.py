from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path

from cpgf.ai.evidence_workers import EVIDENCE_WORKER_VERSION
from cpgf.ai.model_policy import DEFAULT_LLM_MODEL, LLM_MODEL_POLICY_VERSION
from cpgf.ai.orchestrator_normalization import ORCHESTRATOR_NORMALIZATION_VERSION
from cpgf.ai.semantic_orchestrator import (
    ORCHESTRATOR_SYSTEM_PROMPT,
    SEMANTIC_ORCHESTRATOR_POLICY_VERSION,
    SEMANTIC_ORCHESTRATOR_VERSION,
)
from cpgf.ai.web_evidence import (
    WEB_EVIDENCE_POLICY_VERSION,
    WEB_EVIDENCE_WORKER_VERSION,
)
from cpgf.benchmark.orchestration_holdout_v2 import (
    FROZEN_PRIOR_BENCHMARK_PATHS,
    ORCHESTRATION_HOLDOUT_V2_VERSION,
    load_orchestration_holdout_v2,
    orchestration_holdout_v2_sha256,
    validate_frozen_prior_benchmarks_v2,
    validate_orchestration_holdout_v2_capabilities,
    validate_orchestration_holdout_v2_novelty,
)
from cpgf.version import EVIDENCE_CONTRACT_VERSION

BENCHMARK = Path("data/benchmarks/orchestration_holdout_v2_0_0.csv.gz")
MANIFEST = Path("data/manifests/orchestration_holdout_2_0_0.json")
SOURCES = {
    "orchestrator_source_git_blob_sha": Path("src/cpgf/ai/semantic_orchestrator.py"),
    "orchestrator_normalization_source_git_blob_sha": Path(
        "src/cpgf/ai/orchestrator_normalization.py"
    ),
    "model_policy_source_git_blob_sha": Path("src/cpgf/ai/model_policy.py"),
    "evidence_contract_source_git_blob_sha": Path("src/cpgf/ai/evidence_contracts.py"),
    "evidence_worker_source_git_blob_sha": Path("src/cpgf/ai/evidence_workers.py"),
    "tool_registry_source_git_blob_sha": Path("src/cpgf/ai/tools/registry.py"),
    "web_evidence_source_git_blob_sha": Path("src/cpgf/ai/web_evidence.py"),
    "ai_contract_source_git_blob_sha": Path("src/cpgf/ai/contracts.py"),
    "knowledge_models_source_git_blob_sha": Path("src/cpgf/knowledge/models.py"),
    "pyproject_source_git_blob_sha": Path("pyproject.toml"),
}


def _git_blob_sha(path: Path) -> str:
    content = path.read_bytes()
    return hashlib.sha1(f"blob {len(content)}\0".encode() + content).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Valida o freeze prospectivo do OH2 sem chamar LLM, plan_evidence, "
            "workers, Retriever, Web ou SQL."
        )
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if manifest["status"] != "FROZEN_BEFORE_MEASUREMENT":
        raise ValueError("Estado inválido antes da primeira medição do OH2")
    if ORCHESTRATION_HOLDOUT_V2_VERSION != "2.0.0":
        raise ValueError("Versão inesperada do OH2")
    if manifest["version"] != ORCHESTRATION_HOLDOUT_V2_VERSION:
        raise ValueError("Manifesto e módulo do OH2 divergem")

    actual_sha = orchestration_holdout_v2_sha256(BENCHMARK)
    if actual_sha != manifest["benchmark"]["sha256"]:
        raise ValueError(f"Benchmark OH2 divergiu do manifesto: {actual_sha}")

    suite = load_orchestration_holdout_v2(BENCHMARK)
    capabilities = validate_orchestration_holdout_v2_capabilities(suite)

    frozen_prior = validate_frozen_prior_benchmarks_v2()
    manifest_prior = manifest["novelty"]["prior_benchmark_paths"]
    expected_prior = [str(path) for path in FROZEN_PRIOR_BENCHMARK_PATHS]
    if manifest_prior != expected_prior:
        raise ValueError("Lista histórica do manifesto divergiu do universo congelado no código")
    if frozen_prior["benchmarks"] != manifest["novelty"]["prior_benchmarks_expected"]:
        raise ValueError("Quantidade congelada de benchmarks históricos divergiu")
    if frozen_prior["questions"] != manifest["novelty"]["prior_questions_expected"]:
        raise ValueError(
            f"Universo histórico inesperado: {frozen_prior['questions']} perguntas"
        )
    if not frozen_prior["includes_oh1"]:
        raise ValueError("OH2 deve comparar novidade explicitamente contra o OH1 conhecido")

    novelty = validate_orchestration_holdout_v2_novelty(
        suite,
        FROZEN_PRIOR_BENCHMARK_PATHS,
        max_similarity_allowed=manifest["novelty"]["prospective_max_similarity"],
    )

    frozen = manifest["candidate_freeze"]
    current_blobs = {name: _git_blob_sha(path) for name, path in SOURCES.items()}
    versions_match = (
        SEMANTIC_ORCHESTRATOR_VERSION == frozen["orchestrator_version"]
        and SEMANTIC_ORCHESTRATOR_POLICY_VERSION
        == frozen["orchestrator_policy_version"]
        and ORCHESTRATOR_NORMALIZATION_VERSION
        == frozen["orchestrator_normalization_version"]
        and EVIDENCE_CONTRACT_VERSION == frozen["evidence_contract_version"]
        and EVIDENCE_WORKER_VERSION == frozen["evidence_worker_version"]
        and WEB_EVIDENCE_WORKER_VERSION == frozen["web_evidence_worker_version"]
        and WEB_EVIDENCE_POLICY_VERSION == frozen["web_evidence_policy_version"]
        and LLM_MODEL_POLICY_VERSION == frozen["model_policy_version"]
        and DEFAULT_LLM_MODEL == frozen["model"]
        and importlib.metadata.version("openai") == frozen["openai_sdk_version"]
        and hashlib.sha256(ORCHESTRATOR_SYSTEM_PROMPT.encode("utf-8")).hexdigest()
        == frozen["orchestrator_system_prompt_sha256"]
    )
    blobs_match = all(current_blobs[name] == frozen[name] for name in SOURCES)
    if not versions_match or not blobs_match:
        raise ValueError(
            "Candidata ou contratos mudaram depois do início da autoria prospectiva do OH2"
        )

    gate = manifest["prospective_acceptance_gate"]
    if not gate["defined_before_first_measurement"]:
        raise ValueError("Gate do OH2 não foi definido prospectivamente")
    if gate["performance_threshold_causes_measurement_workflow_failure"]:
        raise ValueError("Desempenho não pode apagar a primeira medição independente do OH2")

    governance = manifest["governance"]
    required_true = (
        "benchmark_authored_without_candidate_outputs",
        "candidate_specification_frozen_before_benchmark_authoring",
        "first_measurement_must_run_only_after_this_freeze_is_merged",
        "oh1_is_known_and_not_independent",
    )
    if not all(governance[name] for name in required_true):
        raise ValueError("Governança prospectiva incompleta no manifesto OH2")

    payload = {
        "artifact": "orchestration_holdout_v2_preflight",
        "status": "PASS",
        "manifest_status": manifest["status"],
        "benchmark_sha256": actual_sha,
        "benchmark_uncompressed_sha256": manifest["benchmark"]["uncompressed_sha256"],
        "capability_validation": capabilities,
        "frozen_prior_validation": frozen_prior,
        "novelty_validation": novelty,
        "candidate_freeze": frozen,
        "current_candidate": {
            "orchestrator_version": SEMANTIC_ORCHESTRATOR_VERSION,
            "orchestrator_policy_version": SEMANTIC_ORCHESTRATOR_POLICY_VERSION,
            "orchestrator_normalization_version": ORCHESTRATOR_NORMALIZATION_VERSION,
            "evidence_contract_version": EVIDENCE_CONTRACT_VERSION,
            "evidence_worker_version": EVIDENCE_WORKER_VERSION,
            "web_evidence_worker_version": WEB_EVIDENCE_WORKER_VERSION,
            "web_evidence_policy_version": WEB_EVIDENCE_POLICY_VERSION,
            "model_policy_version": LLM_MODEL_POLICY_VERSION,
            "model": DEFAULT_LLM_MODEL,
            "openai_sdk_version": importlib.metadata.version("openai"),
            "orchestrator_system_prompt_sha256": hashlib.sha256(
                ORCHESTRATOR_SYSTEM_PROMPT.encode("utf-8")
            ).hexdigest(),
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
