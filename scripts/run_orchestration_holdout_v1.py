from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path

from cpgf.ai.model_policy import project_llm_model
from cpgf.ai.semantic_orchestrator import OpenAIResponsesOrchestratorProvider
from cpgf.benchmark.orchestration_holdout_measurement_v1 import (
    evaluate_orchestration_acceptance_gate,
    evaluate_orchestration_holdout,
)
from cpgf.benchmark.orchestration_holdout_v1 import (
    load_orchestration_holdout,
    orchestration_holdout_sha256,
)
from cpgf.version import (
    EVIDENCE_CONTRACT_VERSION,
    EVIDENCE_WORKER_VERSION,
    LLM_MODEL_POLICY_VERSION,
    ORCHESTRATION_HOLDOUT_MEASUREMENT_VERSION,
    ORCHESTRATION_HOLDOUT_VERSION,
    SEMANTIC_ORCHESTRATOR_POLICY_VERSION,
    SEMANTIC_ORCHESTRATOR_VERSION,
    WEB_EVIDENCE_POLICY_VERSION,
)

BENCHMARK = Path("data/benchmarks/orchestration_holdout_v1_0_0.csv.gz")
HOLDOUT_MANIFEST = Path("data/manifests/orchestration_holdout_1_0_0.json")
MEASUREMENT_PROTOCOL = Path("data/manifests/orchestration_holdout_measurement_1_0_0.json")
MODEL_POLICY = Path("src/cpgf/ai/model_policy.py")
ORCHESTRATOR = Path("src/cpgf/ai/semantic_orchestrator.py")
EVIDENCE_CONTRACTS = Path("src/cpgf/ai/evidence_contracts.py")
EVIDENCE_WORKERS = Path("src/cpgf/ai/evidence_workers.py")
TOOL_REGISTRY = Path("src/cpgf/ai/tools/registry.py")
WEB_EVIDENCE = Path("src/cpgf/ai/web_evidence.py")
EVALUATOR = Path("src/cpgf/benchmark/orchestration_holdout_measurement_v1.py")
RUNNER = Path("scripts/run_orchestration_holdout_v1.py")


def _load(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _git_blob_sha(path: Path) -> str:
    content = path.read_bytes()
    return hashlib.sha1(f"blob {len(content)}\0".encode() + content).hexdigest()


def _require_official_github_main_run() -> dict[str, str | None]:
    if os.getenv("GITHUB_ACTIONS") != "true":
        raise RuntimeError("a medição oficial OH1 só pode executar no GitHub Actions")
    if os.getenv("GITHUB_REF") != "refs/heads/main":
        raise RuntimeError("a medição oficial OH1 só pode executar a partir de main")
    if os.getenv("GITHUB_EVENT_NAME") != "push":
        raise RuntimeError("a primeira medição OH1 é acionada somente pelo merge do harness em main")
    if not os.getenv("GITHUB_RUN_ID"):
        raise RuntimeError("GITHUB_RUN_ID ausente")
    return {
        "github_run_id": os.getenv("GITHUB_RUN_ID"),
        "github_run_attempt": os.getenv("GITHUB_RUN_ATTEMPT"),
        "github_sha": os.getenv("GITHUB_SHA"),
        "github_ref": os.getenv("GITHUB_REF"),
        "github_event_name": os.getenv("GITHUB_EVENT_NAME"),
        "github_workflow": os.getenv("GITHUB_WORKFLOW"),
    }


def _validate_freezes() -> tuple[dict[str, object], dict[str, object]]:
    holdout = _load(HOLDOUT_MANIFEST)
    protocol = _load(MEASUREMENT_PROTOCOL)

    if holdout["version"] != ORCHESTRATION_HOLDOUT_VERSION:
        raise ValueError("versão do Orchestration Holdout divergiu")
    if holdout["status"] != "FROZEN_BEFORE_MEASUREMENT":
        raise ValueError("OH1 precisa permanecer congelado antes da primeira medição")
    if holdout["measurement"]["performed"] is not False:
        raise ValueError("manifesto OH1 indica medição anterior")
    if orchestration_holdout_sha256(BENCHMARK) != holdout["benchmark"]["sha256"]:
        raise ValueError("benchmark OH1 divergiu do SHA congelado")

    if protocol["version"] != ORCHESTRATION_HOLDOUT_MEASUREMENT_VERSION:
        raise ValueError("versão do protocolo OH1 divergiu")
    if protocol["status"] != "MEASUREMENT_HARNESS_FROZEN_BEFORE_FIRST_OH1_LLM_RUN":
        raise ValueError("harness OH1 não está no estado congelado")
    if protocol["measurement"]["performed"] is not False:
        raise ValueError("protocolo OH1 já registra medição realizada")
    if protocol["benchmark"]["sha256"] != holdout["benchmark"]["sha256"]:
        raise ValueError("protocolo referencia benchmark OH1 diferente")

    frozen = protocol["candidate_freeze"]
    current_blobs = {
        "model_policy_source_git_blob_sha": _git_blob_sha(MODEL_POLICY),
        "orchestrator_source_git_blob_sha": _git_blob_sha(ORCHESTRATOR),
        "evidence_contract_source_git_blob_sha": _git_blob_sha(EVIDENCE_CONTRACTS),
        "evidence_worker_source_git_blob_sha": _git_blob_sha(EVIDENCE_WORKERS),
        "tool_registry_source_git_blob_sha": _git_blob_sha(TOOL_REGISTRY),
        "web_evidence_source_git_blob_sha": _git_blob_sha(WEB_EVIDENCE),
    }
    for key, actual in current_blobs.items():
        if frozen[key] != actual:
            raise ValueError(f"dependência congelada divergiu: {key}")

    if frozen["model"] != project_llm_model() or project_llm_model() != "gpt-4o-mini":
        raise ValueError("modelo governado divergiu do freeze OH1")
    if frozen["model_policy_version"] != LLM_MODEL_POLICY_VERSION:
        raise ValueError("versão da política de modelo divergiu")
    if frozen["orchestrator_version"] != SEMANTIC_ORCHESTRATOR_VERSION:
        raise ValueError("versão do Orchestrator divergiu")
    if frozen["orchestrator_policy_version"] != SEMANTIC_ORCHESTRATOR_POLICY_VERSION:
        raise ValueError("política do Orchestrator divergiu")
    if frozen["evidence_contract_version"] != EVIDENCE_CONTRACT_VERSION:
        raise ValueError("contrato de evidência divergiu")
    if frozen["evidence_worker_version"] != EVIDENCE_WORKER_VERSION:
        raise ValueError("worker de evidência divergiu")
    if frozen["web_evidence_policy_version"] != WEB_EVIDENCE_POLICY_VERSION:
        raise ValueError("política WEB divergiu")

    harness = protocol["harness_freeze"]
    if harness["evaluator_source_git_blob_sha"] != _git_blob_sha(EVALUATOR):
        raise ValueError("evaluator OH1 divergiu do harness congelado")
    if harness["runner_source_git_blob_sha"] != _git_blob_sha(RUNNER):
        raise ValueError("runner OH1 divergiu do harness congelado")

    expected_sdk = protocol["execution"]["openai_sdk_version"]
    if importlib.metadata.version("openai") != expected_sdk:
        raise ValueError("OpenAI SDK divergiu do protocolo congelado")

    return holdout, protocol


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Executa a primeira medição independente do Semantic Evidence Orchestrator no OH1."
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    if args.output.exists():
        raise FileExistsError("o artifact de medição OH1 não pode ser sobrescrito")

    run_context = _require_official_github_main_run()
    holdout, protocol = _validate_freezes()
    execution = protocol["execution"]
    if int(execution["expected_llm_calls"]) != 168:
        raise ValueError("protocolo OH1 precisa congelar exatamente 168 chamadas LLM")
    if int(execution["llm_repetitions"]) != 3:
        raise ValueError("OH1 exige três repetições LLM")
    if execution["model"] != "gpt-4o-mini":
        raise ValueError("modelo do protocolo OH1 deve ser gpt-4o-mini")

    suite = load_orchestration_holdout(BENCHMARK)
    provider = OpenAIResponsesOrchestratorProvider()
    evaluation = evaluate_orchestration_holdout(
        suite,
        provider=provider,
        repeats=int(execution["llm_repetitions"]),
    )
    gate = evaluate_orchestration_acceptance_gate(
        evaluation,
        protocol["prospective_acceptance_gate"],
    )

    payload = {
        "artifact": "orchestration_holdout_first_measurement",
        "version": ORCHESTRATION_HOLDOUT_MEASUREMENT_VERSION,
        "status": "INDEPENDENT_OH1_FIRST_MEASUREMENT",
        "run_context": run_context,
        "benchmark": {
            "version": holdout["version"],
            "sha256": holdout["benchmark"]["sha256"],
            "uncompressed_sha256": holdout["benchmark"]["uncompressed_sha256"],
            "cases": len(suite.cases),
            "independent_for_orchestrator_before_this_run": True,
        },
        "candidate": {
            "name": protocol["candidate_freeze"]["name"],
            "orchestrator_version": SEMANTIC_ORCHESTRATOR_VERSION,
            "orchestrator_policy_version": SEMANTIC_ORCHESTRATOR_POLICY_VERSION,
            "model_requested": project_llm_model(),
            "openai_sdk_version": importlib.metadata.version("openai"),
        },
        "protocol": {
            "manifest_path": str(MEASUREMENT_PROTOCOL),
            "prospective_gate_defined_before_measurement": True,
            "merge_triggered_main_run_is_official_measurement": True,
            "reruns_are_not_new_independent_measurements": True,
        },
        "evaluation": evaluation,
        "prospective_gate": gate,
        "governance": {
            "result_preserved_regardless_of_gate": True,
            "prompt_tuning_after_result_allowed_for_same_oh1_independence_claim": False,
            "model_change_after_result_allowed_for_same_oh1_independence_claim": False,
            "orchestrator_policy_change_after_result_allowed_for_same_oh1_independence_claim": False,
            "workers_called": False,
            "retriever_called": False,
            "web_search_called": False,
            "sql_executed": False,
            "final_answer_llm_called": False,
            "production_activation": False,
            "gate_pass_does_not_imply_production_readiness": True,
        },
    }

    text = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(text + "\n", encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
