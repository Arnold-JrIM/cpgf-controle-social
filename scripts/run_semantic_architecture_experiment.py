from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path

from cpgf.ai.semantic_experiment import OpenAIResponsesSemanticProvider
from cpgf.benchmark.joint_retrieval_v4 import (
    joint_holdout_v4_sha256,
    load_joint_retrieval_holdout_v4,
)
from cpgf.benchmark.semantic_architecture_experiment import (
    SemanticArchitecture,
    evaluate_semantic_architectures,
)
from cpgf.version import (
    RETRIEVAL_PLANNER_VERSION,
    ROUTER_VERSION,
    SEMANTIC_ARCHITECTURE_EXPERIMENT_VERSION,
)

DEFAULT_BENCHMARK = Path("data/benchmarks/joint_retrieval_holdout_v4_0_0.csv")
DEFAULT_JH4_MANIFEST = Path("data/manifests/joint_retrieval_holdout_4_0_0.json")
DEFAULT_PROTOCOL = Path("data/manifests/semantic_architecture_experiment_1_0_0.json")
ROUTER_SOURCE = Path("src/cpgf/ai/router.py")
PLANNER_SOURCE = Path("src/cpgf/ai/retrieval_planner.py")


def _git_blob_sha(path: Path) -> str:
    content = path.read_bytes()
    header = f"blob {len(content)}\0".encode()
    return hashlib.sha1(header + content).hexdigest()


def _load(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _selection(result: dict[str, object], protocol: dict[str, object]) -> dict[str, object]:
    rules = protocol["prospective_selection_rule"]
    aggregate = result["aggregate"]
    stability = result["stability"]
    baseline = float(aggregate[SemanticArchitecture.DETERMINISTIC.value]["mean_joint_exact_rate"])
    eligible: dict[str, dict[str, object]] = {}

    for architecture in (
        SemanticArchitecture.LLM_ROUTE,
        SemanticArchitecture.HYBRID_ADJUDICATED,
    ):
        name = architecture.value
        stats = aggregate[name]
        stable = stability[name]
        checks = {
            "zero_schema_violations": int(stats["schema_violations"]) == 0,
            "minimum_absolute_gain_met": float(stats["mean_joint_exact_rate"])
            >= baseline + float(rules["minimum_absolute_joint_gain_over_A"]),
            "minimum_stability_met": float(stable["mean_modal_share"])
            >= float(rules["minimum_mean_modal_stability"]),
        }
        eligible[name] = {
            "eligible": all(checks.values()),
            "checks": checks,
            "mean_joint_exact_rate": stats["mean_joint_exact_rate"],
            "worst_joint_exact_rate": stats["worst_joint_exact_rate"],
            "mean_modal_share": stable["mean_modal_share"],
        }

    candidates = [name for name, item in eligible.items() if item["eligible"]]
    winner: str | None = None
    if candidates:
        candidates.sort(
            key=lambda name: float(eligible[name]["mean_joint_exact_rate"]),
            reverse=True,
        )
        winner = candidates[0]
        if len(candidates) > 1:
            top = float(eligible[candidates[0]]["mean_joint_exact_rate"])
            second = float(eligible[candidates[1]]["mean_joint_exact_rate"])
            if abs(top - second) <= float(rules["tie_margin"]):
                winner = SemanticArchitecture.LLM_ROUTE.value

    return {
        "baseline_A_joint_exact_rate": baseline,
        "candidates": eligible,
        "selected_for_future_jh5_candidate": winner,
        "selection_is_on_known_development_material": True,
        "selection_is_not_generalization_evidence": True,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Executa experimento controlado A/B/C sobre JH4 conhecido."
    )
    parser.add_argument("--benchmark", type=Path, default=DEFAULT_BENCHMARK)
    parser.add_argument("--jh4-manifest", type=Path, default=DEFAULT_JH4_MANIFEST)
    parser.add_argument("--protocol", type=Path, default=DEFAULT_PROTOCOL)
    parser.add_argument("--model", default="gpt-5.6")
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    jh4 = _load(args.jh4_manifest)
    protocol = _load(args.protocol)
    if jh4["status"] != "MEASURED_INDEPENDENT":
        raise ValueError("JH4 precisa estar medido e conhecido antes do experimento com LLM")
    if protocol["status"] != "PROTOCOL_FROZEN_BEFORE_LLM_RUN":
        raise ValueError("protocolo precisa estar congelado antes da primeira chamada ao LLM")
    if protocol["version"] != SEMANTIC_ARCHITECTURE_EXPERIMENT_VERSION:
        raise ValueError("versão do protocolo divergiu da versão do código")
    if joint_holdout_v4_sha256(args.benchmark) != jh4["benchmark"]["sha256"]:
        raise ValueError("benchmark JH4 divergiu do SHA congelado")

    frozen = jh4["frozen_flow"]
    if ROUTER_VERSION != frozen["router_version"] or RETRIEVAL_PLANNER_VERSION != frozen[
        "retrieval_planner_version"
    ]:
        raise ValueError("Router/Planner correntes divergem do fluxo congelado do JH4")
    if _git_blob_sha(ROUTER_SOURCE) != frozen["router_source_git_blob_sha"]:
        raise ValueError("blob do Router divergiu do fluxo congelado do JH4")
    if _git_blob_sha(PLANNER_SOURCE) != frozen["retrieval_planner_source_git_blob_sha"]:
        raise ValueError("blob do Planner divergiu do fluxo congelado do JH4")
    if args.repeats != int(protocol["execution"]["llm_repetitions"]):
        raise ValueError("número de repetições precisa coincidir com o protocolo congelado")
    if args.model != protocol["execution"]["model_alias"]:
        raise ValueError("modelo precisa coincidir com o alias congelado no protocolo")

    suite = load_joint_retrieval_holdout_v4(args.benchmark)
    provider = OpenAIResponsesSemanticProvider(model=args.model)
    result = evaluate_semantic_architectures(suite, provider=provider, repeats=args.repeats)
    selection = _selection(result, protocol)

    payload = {
        "artifact": "semantic_architecture_experiment",
        "version": SEMANTIC_ARCHITECTURE_EXPERIMENT_VERSION,
        "status": "KNOWN_MATERIAL_ARCHITECTURE_SELECTION",
        "benchmark": {
            "version": jh4["version"],
            "sha256": jh4["benchmark"]["sha256"],
            "already_known_before_llm_experiment": True,
        },
        "frozen_deterministic_flow": frozen,
        "provider": {
            "type": "openai_responses_structured_outputs",
            "requested_model": args.model,
            "openai_sdk_version": importlib.metadata.version("openai"),
            "external_tools_enabled": False,
            "store": False,
        },
        "result": result,
        "selection": selection,
        "governance": {
            "production_llm_activation": False,
            "production_graph_modified": False,
            "retriever_called": False,
            "benchmark_oracle_changed": False,
            "jh5_exists_before_selection": False,
            "future_generalization_claim_requires_new_jh5": True,
        },
    }

    text = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(text + "\n", encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
