from __future__ import annotations

import hashlib
import json
from pathlib import Path

from cpgf.ai.router import Route
from cpgf.ai.semantic_experiment import (
    SemanticCallMetadata,
    SemanticRouteCall,
    SemanticRouteOutput,
)
from cpgf.benchmark.joint_retrieval_v5 import load_joint_retrieval_holdout_v5
from cpgf.benchmark.semantic_candidate_jh5 import (
    evaluate_candidate_b_jh5,
    evaluate_jh5_acceptance_gate,
)
from cpgf.version import SEMANTIC_CANDIDATE_JH5_MEASUREMENT_VERSION

BENCHMARK = Path("data/benchmarks/joint_retrieval_holdout_v5_0_0.csv")
PROTOCOL = Path("data/manifests/semantic_candidate_jh5_measurement_1_0_0.json")
CANDIDATE = Path("data/manifests/semantic_candidate_b_1_0_0.json")
PROVIDER = Path("src/cpgf/ai/semantic_experiment.py")
PLANNER = Path("src/cpgf/ai/retrieval_planner.py")
ROUTER = Path("src/cpgf/ai/router.py")
EVALUATOR = Path("src/cpgf/benchmark/semantic_candidate_jh5.py")
RUNNER = Path("scripts/run_semantic_candidate_jh5.py")


def _git_blob_sha(path: Path) -> str:
    content = path.read_bytes()
    return hashlib.sha1(f"blob {len(content)}\0".encode() + content).hexdigest()


def _protocol() -> dict[str, object]:
    return json.loads(PROTOCOL.read_text(encoding="utf-8"))


class GoldRouteProvider:
    model = "gpt-4o-mini-2024-07-18"

    def __init__(self) -> None:
        suite = load_joint_retrieval_holdout_v5(BENCHMARK)
        self.routes = {case.question: case.expected_route for case in suite.cases}
        self.calls = 0

    def classify_route(self, question: str) -> SemanticRouteCall:
        self.calls += 1
        return SemanticRouteCall(
            output=SemanticRouteOutput(
                route=self.routes[question],
                reason="oracle offline para validar exclusivamente o harness",
            ),
            metadata=SemanticCallMetadata(
                response_id=f"fake-{self.calls}",
                response_model=self.model,
                input_tokens=10,
                output_tokens=2,
                latency_ms=1.0,
            ),
        )

    def adjudicate_plan(self, *args: object, **kwargs: object) -> object:
        raise AssertionError("a candidata B não pode chamar adjudicate_plan")


class FailingProvider:
    model = "gpt-4o-mini-2024-07-18"

    def classify_route(self, question: str) -> SemanticRouteCall:
        raise RuntimeError("falha simulada")

    def adjudicate_plan(self, *args: object, **kwargs: object) -> object:
        raise AssertionError("a candidata B não pode chamar adjudicate_plan")


def test_measurement_protocol_freezes_candidate_harness_and_execution() -> None:
    p = _protocol()
    assert p["version"] == SEMANTIC_CANDIDATE_JH5_MEASUREMENT_VERSION == "1.0.0"
    assert p["status"] == "MEASUREMENT_HARNESS_FROZEN_BEFORE_FIRST_JH5_LLM_RUN"

    assert p["benchmark"]["sha256"] == (
        "2695be52ff403043c394f0ca7f9f0a47f209fd2016172586146c69adf5595354"
    )
    candidate = p["candidate_freeze"]
    assert candidate["manifest_git_blob_sha"] == _git_blob_sha(CANDIDATE)
    assert candidate["provider_source_git_blob_sha"] == _git_blob_sha(PROVIDER)
    assert candidate["planner_source_git_blob_sha"] == _git_blob_sha(PLANNER)
    assert candidate["router_source_git_blob_sha"] == _git_blob_sha(ROUTER)

    harness = p["harness_freeze"]
    assert harness["evaluator_source_git_blob_sha"] == _git_blob_sha(EVALUATOR)
    assert harness["runner_source_git_blob_sha"] == _git_blob_sha(RUNNER)

    execution = p["execution"]
    assert execution["model"] == "gpt-4o-mini-2024-07-18"
    assert execution["openai_sdk_version"] == "3.1.0"
    assert execution["llm_repetitions"] == 3
    assert execution["expected_llm_calls"] == 144
    assert execution["structured_outputs_strict"] is True
    assert execution["external_tools_enabled"] is False
    assert execution["workflow_dispatch_has_model_or_repeat_overrides"] is False
    assert p["measurement"]["performed"] is False


def test_offline_oracle_validates_b_route_only_harness_without_external_llm() -> None:
    suite = load_joint_retrieval_holdout_v5(BENCHMARK)
    provider = GoldRouteProvider()
    result = evaluate_candidate_b_jh5(suite, provider=provider, repeats=3)

    assert result["cases"] == 48
    assert provider.calls == 144
    assert result["candidate_B"]["aggregate"]["llm_calls"] == 144
    assert result["candidate_B"]["aggregate"]["schema_violations"] == 0
    assert result["candidate_B"]["aggregate"]["mean_route_exact_rate"] == 1.0
    assert result["candidate_B"]["stability"]["mean_modal_share"] == 1.0
    assert result["candidate_B"]["stability"]["all_repetitions_identical_cases"] == 48
    assert result["governance"]["retriever_called"] is False
    assert result["governance"]["external_tools_available_to_llm"] is False


def test_gate_logic_is_prospective_and_conjunctive() -> None:
    suite = load_joint_retrieval_holdout_v5(BENCHMARK)
    evaluation = evaluate_candidate_b_jh5(
        suite,
        provider=GoldRouteProvider(),
        repeats=3,
    )
    permissive = {
        "schema_violations_allowed": 0,
        "minimum_B_mean_joint_exact_rate": 0.0,
        "minimum_B_absolute_joint_gain_over_A": -1.0,
        "minimum_B_mean_route_exact_rate": 1.0,
        "minimum_B_mean_modal_stability": 1.0,
        "minimum_each_category_B_mean_joint_exact_rate": 0.0,
    }
    passed = evaluate_jh5_acceptance_gate(evaluation, permissive)
    assert passed["passed"] is True

    strict = {**permissive, "minimum_B_mean_route_exact_rate": 1.01}
    failed = evaluate_jh5_acceptance_gate(evaluation, strict)
    assert failed["passed"] is False
    assert failed["checks"]["minimum_B_mean_route_exact_rate"] is False


def test_provider_failures_are_preserved_as_schema_violations() -> None:
    suite = load_joint_retrieval_holdout_v5(BENCHMARK)
    result = evaluate_candidate_b_jh5(
        suite,
        provider=FailingProvider(),
        repeats=3,
    )

    assert result["candidate_B"]["aggregate"]["llm_calls"] == 144
    assert result["candidate_B"]["aggregate"]["schema_violations"] == 144
    assert len(result["candidate_B"]["errors"]) == 144
    assert result["candidate_B"]["aggregate"]["mean_route_exact_rate"] == 0.0
