from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from cpgf.ai.evidence_contracts import EvidenceSource
from cpgf.ai.semantic_orchestrator import (
    DataSelection,
    KnowledgeSelection,
    OrchestratorCallMetadata,
    OrchestratorDecision,
    OrchestratorDecisionCall,
    WebSelection,
)
from cpgf.benchmark.orchestration_holdout_measurement_v1 import (
    ORCHESTRATION_HOLDOUT_MEASUREMENT_VERSION,
    evaluate_orchestration_acceptance_gate,
    evaluate_orchestration_holdout,
)
from cpgf.benchmark.orchestration_holdout_v1 import load_orchestration_holdout

BENCHMARK = Path("data/benchmarks/orchestration_holdout_v1_0_0.csv.gz")
PROTOCOL = Path("data/manifests/orchestration_holdout_measurement_1_0_0.json")


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
            reason="plano oracle prospectivo",
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
                response_id=f"resp-{self.calls}",
                response_model="gpt-4o-mini",
                input_tokens=10,
                output_tokens=5,
                latency_ms=1.0,
            ),
        )


class FailingProvider:
    model = "gpt-4o-mini"

    def __init__(self):
        self.calls = 0

    def decide(self, question: str) -> OrchestratorDecisionCall:
        self.calls += 1
        raise RuntimeError("provider offline para teste")


def _git_blob_sha(path: Path) -> str:
    content = path.read_bytes()
    return hashlib.sha1(f"blob {len(content)}\0".encode() + content).hexdigest()


def test_oracle_provider_reaches_perfect_measurement_and_gate():
    suite = load_orchestration_holdout(BENCHMARK)
    provider = OracleProvider(suite)
    evaluation = evaluate_orchestration_holdout(suite, provider=provider, repeats=3)
    rules = json.loads(PROTOCOL.read_text(encoding="utf-8"))["prospective_acceptance_gate"]
    gate = evaluate_orchestration_acceptance_gate(evaluation, rules)

    assert provider.calls == 168
    assert len(evaluation["rows"]) == 168
    assert evaluation["aggregate"]["llm_attempts"] == 168
    assert evaluation["aggregate"]["schema_violations"] == 0
    assert evaluation["aggregate"]["mean_source_set_exact_rate"] == 1.0
    assert evaluation["aggregate"]["mean_source_precision"] == 1.0
    assert evaluation["aggregate"]["mean_source_recall"] == 1.0
    assert evaluation["aggregate"]["mean_data_tool_exact_rate"] == 1.0
    assert evaluation["aggregate"]["mean_data_arguments_exact_rate"] == 1.0
    assert evaluation["aggregate"]["mean_knowledge_filters_joint_exact_rate"] == 1.0
    assert evaluation["aggregate"]["mean_web_parameters_exact_rate"] == 1.0
    assert evaluation["stability"]["mean_modal_share"] == 1.0
    assert gate["passed"] is True
    assert all(gate["category_checks"].values())


def test_provider_failures_are_preserved_and_fail_gate():
    suite = load_orchestration_holdout(BENCHMARK)
    provider = FailingProvider()
    evaluation = evaluate_orchestration_holdout(suite, provider=provider, repeats=3)
    rules = json.loads(PROTOCOL.read_text(encoding="utf-8"))["prospective_acceptance_gate"]
    gate = evaluate_orchestration_acceptance_gate(evaluation, rules)

    assert provider.calls == 168
    assert evaluation["aggregate"]["provider_failures"] == 168
    assert evaluation["aggregate"]["schema_violations"] == 168
    assert evaluation["aggregate"]["mean_source_set_exact_rate"] == 0.0
    assert gate["passed"] is False
    assert gate["checks"]["zero_schema_violations"] is False


def test_measurement_requires_exactly_three_repetitions():
    suite = load_orchestration_holdout(BENCHMARK)
    with pytest.raises(ValueError, match="três repetições"):
        evaluate_orchestration_holdout(suite, provider=OracleProvider(suite), repeats=2)


def test_protocol_freezes_model_harness_and_no_pr_llm_execution():
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    assert ORCHESTRATION_HOLDOUT_MEASUREMENT_VERSION == "1.0.0"
    assert protocol["status"] == "MEASUREMENT_HARNESS_FROZEN_BEFORE_FIRST_OH1_LLM_RUN"
    assert protocol["execution"]["model"] == "gpt-4o-mini"
    assert protocol["execution"]["llm_repetitions"] == 3
    assert protocol["execution"]["expected_llm_calls"] == 168
    assert protocol["execution"]["workflow_has_model_or_repeat_overrides"] is False
    assert protocol["measurement"]["performed"] is False
    assert protocol["governance"]["no_llm_call_allowed_on_pull_request"] is True
    assert protocol["governance"]["holdout_questions_remain_unseen_by_candidate_during_this_pr"] is True

    evaluator = Path(protocol["harness_freeze"]["evaluator_path"])
    runner = Path(protocol["harness_freeze"]["runner_path"])
    assert _git_blob_sha(evaluator) == protocol["harness_freeze"]["evaluator_source_git_blob_sha"]
    assert _git_blob_sha(runner) == protocol["harness_freeze"]["runner_source_git_blob_sha"]
