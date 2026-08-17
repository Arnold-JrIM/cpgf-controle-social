from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

from cpgf.ai.router import Route, RouteDecision
from cpgf.ai.semantic_experiment import (
    DEFAULT_SEMANTIC_MODEL,
    OpenAIResponsesSemanticProvider,
    SemanticCallMetadata,
    SemanticPlanCall,
    SemanticPlanOutput,
    SemanticRouteCall,
    SemanticRouteOutput,
)
from cpgf.benchmark.joint_retrieval_v4 import load_joint_retrieval_holdout_v4
from cpgf.benchmark.semantic_architecture_experiment import (
    SemanticArchitecture,
    evaluate_semantic_architectures,
)

BENCHMARK = Path("data/benchmarks/joint_retrieval_holdout_v4_0_0.csv")
PROTOCOL = Path("data/manifests/semantic_architecture_experiment_1_0_1.json")
SEMANTIC_SOURCE = Path("src/cpgf/ai/semantic_experiment.py")
EVALUATOR_SOURCE = Path("src/cpgf/benchmark/semantic_architecture_experiment.py")


def _git_blob_sha(path: Path) -> str:
    content = path.read_bytes()
    header = f"blob {len(content)}\0".encode()
    return hashlib.sha1(header + content).hexdigest()


class OracleProvider:
    model = "oracle-test"

    def __init__(self) -> None:
        suite = load_joint_retrieval_holdout_v4(BENCHMARK)
        self.by_question = {case.question: case for case in suite.cases}
        self.metadata = SemanticCallMetadata(
            response_id="fake-response",
            response_model="oracle-test",
            input_tokens=1,
            output_tokens=1,
            latency_ms=1.0,
        )

    def classify_route(self, question: str) -> SemanticRouteCall:
        case = self.by_question[question]
        return SemanticRouteCall(
            output=SemanticRouteOutput(route=case.expected_route, reason="oracle de teste"),
            metadata=self.metadata,
        )

    def adjudicate_plan(
        self,
        question: str,
        *,
        deterministic_decision: RouteDecision,
    ) -> SemanticPlanCall:
        del deterministic_decision
        case = self.by_question[question]
        return SemanticPlanCall(
            output=SemanticPlanOutput(
                route=case.expected_route,
                scopes=case.expected_scopes,
                temporal_statuses=case.expected_temporal_statuses,
                reason="oracle de teste",
            ),
            metadata=self.metadata,
        )


def test_oracle_provider_reproduces_known_bounds_without_api_calls() -> None:
    suite = load_joint_retrieval_holdout_v4(BENCHMARK)
    result = evaluate_semantic_architectures(suite, provider=OracleProvider(), repeats=3)

    a = result["aggregate"][SemanticArchitecture.DETERMINISTIC.value]
    b = result["aggregate"][SemanticArchitecture.LLM_ROUTE.value]
    c = result["aggregate"][SemanticArchitecture.HYBRID_ADJUDICATED.value]

    assert a["mean_joint_exact_rate"] == 18 / 48
    assert b["mean_route_exact_rate"] == 1.0
    assert b["mean_joint_exact_rate"] == 31 / 48
    assert c["mean_joint_exact_rate"] == 1.0
    assert b["schema_violations"] == 0
    assert c["schema_violations"] == 0
    assert b["llm_calls"] == 48 * 3
    assert c["llm_calls"] == 48 * 3
    assert result["stability"][SemanticArchitecture.LLM_ROUTE.value]["mean_modal_share"] == 1.0
    assert (
        result["stability"][SemanticArchitecture.HYBRID_ADJUDICATED.value][
            "mean_modal_share"
        ]
        == 1.0
    )


class _FakeResponses:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []
        self.outputs = [
            json.dumps({"route": "knowledge", "reason": "consulta documental"}),
            json.dumps(
                {
                    "route": "composite",
                    "scopes": ["cpgf_core", "methodology"],
                    "temporal_statuses": ["current", "contextual"],
                    "reason": "combina base normativa e metodológica",
                }
            ),
        ]

    def create(self, **kwargs: object) -> object:
        self.calls.append(kwargs)
        output = self.outputs.pop(0)
        return SimpleNamespace(
            id=f"resp-{len(self.calls)}",
            model=DEFAULT_SEMANTIC_MODEL,
            output_text=output,
            usage=SimpleNamespace(input_tokens=10, output_tokens=5),
        )


class _FakeClient:
    def __init__(self) -> None:
        self.responses = _FakeResponses()


def test_openai_provider_uses_strict_structured_outputs_without_tools() -> None:
    client = _FakeClient()
    provider = OpenAIResponsesSemanticProvider(client=client)

    route_call = provider.classify_route("Qual norma deve orientar o uso do CPGF?")
    assert route_call.output.route == Route.KNOWLEDGE

    plan_call = provider.adjudicate_plan(
        "Que normas e estudos devem ser analisados em conjunto?",
        deterministic_decision=RouteDecision(
            route=Route.KNOWLEDGE,
            reason="proposta determinística de teste",
        ),
    )
    assert plan_call.output.route == Route.COMPOSITE

    assert len(client.responses.calls) == 2
    for call in client.responses.calls:
        assert call["model"] == "gpt-4o-mini-2024-07-18"
        assert call["store"] is False
        assert "tools" not in call
        text = call["text"]
        assert text["format"]["type"] == "json_schema"
        assert text["format"]["strict"] is True


def test_protocol_101_is_frozen_before_first_llm_run() -> None:
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))

    assert protocol["version"] == "1.0.1"
    assert protocol["status"] == "PROTOCOL_FROZEN_BEFORE_LLM_RUN"
    assert protocol["execution"]["model"] == "gpt-4o-mini-2024-07-18"
    assert protocol["execution"]["model_is_snapshot"] is True
    assert protocol["execution"]["llm_repetitions"] == 3
    assert protocol["prospective_selection_rule"]["minimum_absolute_joint_gain_over_A"] == 0.10
    assert protocol["prospective_selection_rule"]["minimum_mean_modal_stability"] == 0.90
    assert protocol["prospective_selection_rule"]["schema_violations_allowed"] == 0
    assert protocol["measurement"]["performed"] is False
    assert protocol["governance"]["production_llm_activation_allowed"] is False
    assert protocol["governance"]["new_independent_jh5_required_after_architecture_selection"] is True

    amendment = protocol["pre_measurement_amendment"]
    assert amendment["previous_model"] == "gpt-5.6"
    assert amendment["selected_model"] == "gpt-4o-mini-2024-07-18"
    assert amendment["workflow_dispatch_runs_observed_before_amendment"] == 0
    assert amendment["architecture_definitions_changed"] is False
    assert amendment["selection_rule_changed"] is False

    freeze = protocol["experimental_code_freeze"]
    assert freeze["semantic_provider_source_git_blob_sha"] == _git_blob_sha(SEMANTIC_SOURCE)
    assert freeze["architecture_evaluator_source_git_blob_sha"] == _git_blob_sha(EVALUATOR_SOURCE)