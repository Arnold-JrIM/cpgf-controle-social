from __future__ import annotations

import argparse
import gzip
import hashlib
import importlib.metadata
import json
from pathlib import Path

from cpgf.ai.evidence_contracts import EvidenceSource
from cpgf.ai.model_policy import DEFAULT_LLM_MODEL, LLM_MODEL_POLICY_VERSION
from cpgf.ai.orchestrator_normalization import ORCHESTRATOR_NORMALIZATION_VERSION
from cpgf.ai.semantic_orchestrator import (
    ORCHESTRATOR_SYSTEM_PROMPT,
    SEMANTIC_ORCHESTRATOR_POLICY_VERSION,
    SEMANTIC_ORCHESTRATOR_VERSION,
    DataSelection,
    KnowledgeSelection,
    OrchestratorCallMetadata,
    OrchestratorDecision,
    OrchestratorDecisionCall,
    WebSelection,
)
from cpgf.ai.web_evidence import WEB_EVIDENCE_POLICY_VERSION, WEB_EVIDENCE_WORKER_VERSION
from cpgf.benchmark.orchestration_holdout_measurement_v1 import evaluate_orchestration_holdout
from cpgf.benchmark.orchestration_holdout_v2 import (
    FROZEN_PRIOR_BENCHMARK_PATHS,
    orchestration_holdout_v2_sha256,
    validate_frozen_prior_benchmarks_v2,
    validate_orchestration_holdout_v2_capabilities,
    validate_orchestration_holdout_v2_novelty,
)
from cpgf.benchmark.orchestration_holdout_v2_patch import (
    CORRECTED_CASE_IDS,
    ORCHESTRATION_HOLDOUT_V2_PATCH_VERSION,
    load_orchestration_holdout_v2_patch,
    validate_question_only_patch,
)
from cpgf.version import EVIDENCE_CONTRACT_VERSION, EVIDENCE_WORKER_VERSION

ORIGINAL = Path("data/benchmarks/orchestration_holdout_v2_0_0.csv.gz")
CORRECTED = Path("data/benchmarks/orchestration_holdout_v2_0_1.csv.gz")
MANIFEST = Path("data/manifests/orchestration_holdout_2_0_1.json")
INVALIDATION = Path("data/manifests/orchestration_holdout_2_0_0_invalidation.json")
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


class OracleProvider:
    model = "gpt-4o-mini"

    def __init__(self, suite):
        self.by_question = {case.question: case for case in suite.cases}
        self.calls = 0

    def decide(self, question: str) -> OrchestratorDecisionCall:
        self.calls += 1
        case = self.by_question[question]
        has_data = EvidenceSource.DATA in case.expected_sources
        has_knowledge = EvidenceSource.KNOWLEDGE in case.expected_sources
        has_web = EvidenceSource.WEB in case.expected_sources
        decision = OrchestratorDecision(
            reason="oracle estático para reachability; não é saída de LLM",
            clarification_question=None,
            data=DataSelection(
                selected=has_data,
                objective="consultar dados governados" if has_data else None,
                tool=case.expected_data_tool if has_data else None,
                parameters=case.expected_data_parameters if has_data else (),
            ),
            knowledge=KnowledgeSelection(
                selected=has_knowledge,
                objective="consultar corpus governado" if has_knowledge else None,
                query_hint="consulta documental prospectiva" if has_knowledge else None,
                scopes=case.expected_knowledge_scopes if has_knowledge else (),
                temporal_statuses=(
                    case.expected_knowledge_temporal_statuses if has_knowledge else ()
                ),
                source_classes=(case.expected_knowledge_source_classes if has_knowledge else ()),
                parameters=(),
            ),
            web=WebSelection(
                selected=has_web,
                objective="consultar fonte oficial atual" if has_web else None,
                query_hint="consulta oficial com freshness" if has_web else None,
                freshness_required=has_web,
                parameters=case.expected_web_parameters if has_web else (),
            ),
        )
        return OrchestratorDecisionCall(
            output=decision,
            metadata=OrchestratorCallMetadata(
                response_id=f"static-oracle-{self.calls}",
                response_model=self.model,
                input_tokens=0,
                output_tokens=0,
                latency_ms=0.0,
            ),
        )


def _git_blob_sha(path: Path) -> str:
    content = path.read_bytes()
    return hashlib.sha1(f"blob {len(content)}\0".encode() + content).hexdigest()


def _uncompressed_sha256(path: Path) -> str:
    with gzip.open(path, "rb") as handle:
        return hashlib.sha256(handle.read()).hexdigest()


def _assert_static_reachability(evaluation: dict[str, object]) -> None:
    aggregate = evaluation["aggregate"]
    required_one = (
        "mean_source_set_exact_rate",
        "mean_source_precision",
        "mean_source_recall",
        "mean_data_tool_exact_rate",
        "mean_data_arguments_exact_rate",
        "mean_knowledge_filters_joint_exact_rate",
        "mean_web_parameters_exact_rate",
        "mean_full_plan_exact_rate",
    )
    failures = {
        name: aggregate[name]
        for name in required_one
        if float(aggregate[name]) != 1.0
    }
    if int(aggregate["schema_violations"]) != 0:
        failures["schema_violations"] = aggregate["schema_violations"]
    if int(aggregate["provider_failures"]) != 0:
        failures["provider_failures"] = aggregate["provider_failures"]
    if int(aggregate["plan_failures"]) != 0:
        failures["plan_failures"] = aggregate["plan_failures"]
    if float(evaluation["stability"]["mean_modal_share"]) != 1.0:
        failures["mean_modal_share"] = evaluation["stability"]["mean_modal_share"]
    if failures:
        bad_rows = [
            {
                "id": row["id"],
                "question": row["question"],
                "expected_sources": row["expected_sources"],
                "predicted_sources": row["predicted_sources"],
                "full_plan_exact": row["full_plan_exact"],
                "warning": row["warning"],
            }
            for row in evaluation["rows"]
            if row["repeat"] == 1 and not row["full_plan_exact"]
        ]
        raise ValueError(
            f"OH2.0.1 ainda contém oracle inalcançável após normalização: "
            f"metrics={failures}; rows={bad_rows}"
        )


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Valida a revisão corretiva OH2.0.1 sem OpenAI ou qualquer saída da candidata."
        )
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    invalidation = json.loads(INVALIDATION.read_text(encoding="utf-8"))

    if manifest["version"] != ORCHESTRATION_HOLDOUT_V2_PATCH_VERSION:
        raise ValueError("manifesto e contrato OH2.0.1 divergem")
    if manifest["status"] != "FROZEN_CORRECTED_BEFORE_MEASUREMENT":
        raise ValueError("OH2.0.1 deve permanecer congelado antes da medição")
    if manifest["measurement"]["performed"] is not False:
        raise ValueError("OH2.0.1 não pode ter sido medido neste PR")
    if invalidation["status"] != "INVALIDATED_BEFORE_MEASUREMENT_STRUCTURAL_REACHABILITY":
        raise ValueError("estado de invalidação do OH2.0.0 divergente")
    if invalidation["measurement_performed"] is not False:
        raise ValueError("OH2.0.0 não pode ter sido medido")

    actual_sha = orchestration_holdout_v2_sha256(CORRECTED)
    actual_uncompressed_sha = _uncompressed_sha256(CORRECTED)
    if actual_sha != manifest["benchmark"]["sha256"]:
        raise ValueError(f"SHA comprimido OH2.0.1 divergiu: {actual_sha}")
    if actual_uncompressed_sha != manifest["benchmark"]["uncompressed_sha256"]:
        raise ValueError(
            f"SHA descomprimido OH2.0.1 divergiu: {actual_uncompressed_sha}"
        )

    patch_validation = validate_question_only_patch(ORIGINAL, CORRECTED)
    if tuple(patch_validation["changed_case_ids"]) != CORRECTED_CASE_IDS:
        raise ValueError("conjunto de correções OH2.0.1 divergiu")

    suite = load_orchestration_holdout_v2_patch(CORRECTED)
    capabilities = validate_orchestration_holdout_v2_capabilities(suite)
    frozen_prior = validate_frozen_prior_benchmarks_v2()
    novelty = validate_orchestration_holdout_v2_novelty(
        suite,
        FROZEN_PRIOR_BENCHMARK_PATHS,
        max_similarity_allowed=manifest["novelty"]["prospective_max_similarity"],
    )

    provider = OracleProvider(suite)
    reachability = evaluate_orchestration_holdout(suite, provider=provider, repeats=3)
    if provider.calls != 168:
        raise ValueError("oracle estático deve avaliar 56 casos x 3 repetições")
    _assert_static_reachability(reachability)

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
        and DEFAULT_LLM_MODEL == frozen["model"] == "gpt-4o-mini"
        and importlib.metadata.version("openai") == frozen["openai_sdk_version"]
        and hashlib.sha256(ORCHESTRATOR_SYSTEM_PROMPT.encode("utf-8")).hexdigest()
        == frozen["orchestrator_system_prompt_sha256"]
    )
    blobs_match = all(current_blobs[name] == frozen[name] for name in SOURCES)
    if not versions_match or not blobs_match:
        raise ValueError("candidata mudou durante a correção prospectiva do OH2")

    governance = manifest["governance"]
    required_true = (
        "correction_authored_without_candidate_outputs",
        "only_question_text_changed",
        "oracles_preserved_exactly",
        "original_invalidated_before_measurement",
        "first_measurement_requires_corrected_freeze_merged",
    )
    if not all(governance[name] for name in required_true):
        raise ValueError("governança da revisão corretiva OH2.0.1 incompleta")

    payload = {
        "artifact": "orchestration_holdout_v2_0_1_preflight",
        "status": "PASS",
        "benchmark_sha256": actual_sha,
        "benchmark_uncompressed_sha256": actual_uncompressed_sha,
        "patch_validation": patch_validation,
        "capability_validation": capabilities,
        "frozen_prior_validation": frozen_prior,
        "novelty_validation": novelty,
        "static_oracle_reachability": {
            "status": "PASS",
            "provider": "STATIC_ORACLE_NO_LLM",
            "calls": provider.calls,
            "mean_source_set_exact_rate": reachability["aggregate"][
                "mean_source_set_exact_rate"
            ],
            "mean_full_plan_exact_rate": reachability["aggregate"][
                "mean_full_plan_exact_rate"
            ],
            "mean_knowledge_filters_joint_exact_rate": reachability["aggregate"][
                "mean_knowledge_filters_joint_exact_rate"
            ],
            "mean_web_parameters_exact_rate": reachability["aggregate"][
                "mean_web_parameters_exact_rate"
            ],
            "schema_violations": reachability["aggregate"]["schema_violations"],
            "mean_modal_share": reachability["stability"]["mean_modal_share"],
        },
        "candidate_freeze_matches": versions_match and blobs_match,
        "governance": {
            "llm_called": False,
            "candidate_provider_called": False,
            "openai_api_called": False,
            "workers_called": False,
            "retriever_called": False,
            "web_called": False,
            "sql_executed": False,
            "measurement_performed": False,
            "candidate_outputs_used_for_correction": False,
        },
    }
    args.output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
