from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path

from cpgf.ai.semantic_experiment import OpenAIResponsesSemanticProvider
from cpgf.benchmark.joint_retrieval_v5 import (
    joint_holdout_v5_sha256,
    load_joint_retrieval_holdout_v5,
)
from cpgf.benchmark.semantic_candidate_jh5 import (
    evaluate_candidate_b_jh5,
    evaluate_jh5_acceptance_gate,
)
from cpgf.version import (
    JOINT_RETRIEVAL_HOLDOUT_V5_VERSION,
    RETRIEVAL_PLANNER_VERSION,
    ROUTER_VERSION,
    SEMANTIC_CANDIDATE_JH5_MEASUREMENT_VERSION,
    SEMANTIC_CANDIDATE_VERSION,
)

BENCHMARK = Path("data/benchmarks/joint_retrieval_holdout_v5_0_0.csv")
JH5_MANIFEST = Path("data/manifests/joint_retrieval_holdout_5_0_0.json")
CANDIDATE_MANIFEST = Path("data/manifests/semantic_candidate_b_1_0_0.json")
MEASUREMENT_PROTOCOL = Path(
    "data/manifests/semantic_candidate_jh5_measurement_1_0_0.json"
)
PROVIDER = Path("src/cpgf/ai/semantic_experiment.py")
PLANNER = Path("src/cpgf/ai/retrieval_planner.py")
ROUTER = Path("src/cpgf/ai/router.py")
EVALUATOR = Path("src/cpgf/benchmark/semantic_candidate_jh5.py")
RUNNER = Path("scripts/run_semantic_candidate_jh5.py")


def _load(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _git_blob_sha(path: Path) -> str:
    content = path.read_bytes()
    return hashlib.sha1(f"blob {len(content)}\0".encode() + content).hexdigest()


def _require_official_github_main_run() -> dict[str, str | None]:
    if os.getenv("GITHUB_ACTIONS") != "true":
        raise RuntimeError("a medição oficial JH5 só pode executar no GitHub Actions")
    if os.getenv("GITHUB_REF") != "refs/heads/main":
        raise RuntimeError("a medição oficial JH5 só pode executar a partir de main")
    if not os.getenv("GITHUB_RUN_ID"):
        raise RuntimeError("GITHUB_RUN_ID ausente")
    return {
        "github_run_id": os.getenv("GITHUB_RUN_ID"),
        "github_run_attempt": os.getenv("GITHUB_RUN_ATTEMPT"),
        "github_sha": os.getenv("GITHUB_SHA"),
        "github_ref": os.getenv("GITHUB_REF"),
        "github_workflow": os.getenv("GITHUB_WORKFLOW"),
    }


def _validate_freezes() -> tuple[dict[str, object], dict[str, object], dict[str, object]]:
    jh5 = _load(JH5_MANIFEST)
    candidate = _load(CANDIDATE_MANIFEST)
    protocol = _load(MEASUREMENT_PROTOCOL)

    if jh5["version"] != JOINT_RETRIEVAL_HOLDOUT_V5_VERSION:
        raise ValueError("versão JH5 divergiu")
    if jh5["status"] != "FROZEN_BEFORE_MEASUREMENT":
        raise ValueError("JH5 precisa permanecer congelado antes da primeira medição")
    if jh5["measurement"]["performed"] is not False:
        raise ValueError("manifesto JH5 indica medição anterior")
    if joint_holdout_v5_sha256(BENCHMARK) != jh5["benchmark"]["sha256"]:
        raise ValueError("benchmark JH5 divergiu do SHA congelado")
    observed = jh5["novelty"]["observed_preflight"]
    if not observed or observed["status"] != "PASS":
        raise ValueError("preflight de novidade JH5 não está registrado como PASS")

    if candidate["version"] != SEMANTIC_CANDIDATE_VERSION:
        raise ValueError("versão da candidata B divergiu")
    if candidate["status"] != "CANDIDATE_FROZEN_BEFORE_JH5_AUTHORING":
        raise ValueError("candidata B não está no estado congelado esperado")
    if _git_blob_sha(CANDIDATE_MANIFEST) != jh5["candidate_freeze"]["manifest_git_blob_sha"]:
        raise ValueError("manifesto da candidata divergiu do freeze JH5")

    if protocol["version"] != SEMANTIC_CANDIDATE_JH5_MEASUREMENT_VERSION:
        raise ValueError("versão do protocolo de medição divergiu")
    if protocol["status"] != "MEASUREMENT_HARNESS_FROZEN_BEFORE_FIRST_JH5_LLM_RUN":
        raise ValueError("harness de medição não está no estado congelado")
    if protocol["measurement"]["performed"] is not False:
        raise ValueError("protocolo já registra medição realizada")
    if protocol["benchmark"]["sha256"] != jh5["benchmark"]["sha256"]:
        raise ValueError("protocolo referencia benchmark JH5 diferente")

    frozen = protocol["candidate_freeze"]
    if frozen["manifest_git_blob_sha"] != _git_blob_sha(CANDIDATE_MANIFEST):
        raise ValueError("manifesto da candidata não corresponde ao protocolo")
    if frozen["provider_source_git_blob_sha"] != _git_blob_sha(PROVIDER):
        raise ValueError("Provider divergiu da candidata congelada")
    if frozen["planner_source_git_blob_sha"] != _git_blob_sha(PLANNER):
        raise ValueError("Planner divergiu da candidata congelada")
    if frozen["router_source_git_blob_sha"] != _git_blob_sha(ROUTER):
        raise ValueError("Router/type dependency divergiu da candidata congelada")

    harness = protocol["harness_freeze"]
    if harness["evaluator_source_git_blob_sha"] != _git_blob_sha(EVALUATOR):
        raise ValueError("evaluator JH5 divergiu do harness congelado")
    if harness["runner_source_git_blob_sha"] != _git_blob_sha(RUNNER):
        raise ValueError("runner JH5 divergiu do harness congelado")

    if RETRIEVAL_PLANNER_VERSION != frozen["planner_version"]:
        raise ValueError("versão do Planner divergiu")
    if ROUTER_VERSION != frozen["router_version"]:
        raise ValueError("versão do Router divergiu")

    expected_sdk = protocol["execution"]["openai_sdk_version"]
    if importlib.metadata.version("openai") != expected_sdk:
        raise ValueError("OpenAI SDK divergiu do protocolo congelado")

    return jh5, candidate, protocol


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Executa a primeira medição independente da candidata B no JH5."
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    if args.output.exists():
        raise FileExistsError("o artifact de medição não pode ser sobrescrito")

    run_context = _require_official_github_main_run()
    jh5, candidate, protocol = _validate_freezes()

    execution = protocol["execution"]
    if int(execution["expected_llm_calls"]) != 144:
        raise ValueError("protocolo precisa congelar exatamente 144 chamadas LLM")
    if int(execution["llm_repetitions"]) != 3:
        raise ValueError("JH5 exige três repetições LLM")
    if execution["model"] != candidate["candidate"]["model"]:
        raise ValueError("modelo do protocolo divergiu da candidata congelada")

    suite = load_joint_retrieval_holdout_v5(BENCHMARK)
    provider = OpenAIResponsesSemanticProvider(model=str(execution["model"]))
    evaluation = evaluate_candidate_b_jh5(
        suite,
        provider=provider,
        repeats=int(execution["llm_repetitions"]),
    )
    gate = evaluate_jh5_acceptance_gate(
        evaluation,
        protocol["prospective_acceptance_gate"],
    )

    payload = {
        "artifact": "semantic_candidate_jh5_measurement",
        "version": SEMANTIC_CANDIDATE_JH5_MEASUREMENT_VERSION,
        "status": "INDEPENDENT_JH5_FIRST_MEASUREMENT",
        "run_context": run_context,
        "benchmark": {
            "version": jh5["version"],
            "sha256": jh5["benchmark"]["sha256"],
            "cases": len(suite.cases),
            "independent_for_candidate_B_before_this_run": True,
        },
        "candidate": {
            "name": candidate["candidate"]["name"],
            "version": candidate["version"],
            "model_requested": execution["model"],
            "openai_sdk_version": importlib.metadata.version("openai"),
            "provider": candidate["candidate"]["provider"],
            "planner_version": candidate["deterministic_planner"]["version"],
            "router_type_dependency_version": candidate["route_type_dependency"][
                "router_version"
            ],
        },
        "protocol": {
            "manifest_path": str(MEASUREMENT_PROTOCOL),
            "prospective_gate_defined_before_measurement": True,
            "first_completed_dispatch_is_official_measurement": True,
            "reruns_are_not_independent_measurements": True,
        },
        "evaluation": evaluation,
        "prospective_gate": gate,
        "governance": {
            "result_preserved_regardless_of_gate": True,
            "prompt_tuning_after_result_allowed": False,
            "model_change_after_result_allowed_for_same_jh5_independence_claim": False,
            "planner_change_after_result_allowed_for_same_jh5_independence_claim": False,
            "retriever_called": False,
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
