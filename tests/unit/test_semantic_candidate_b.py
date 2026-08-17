from __future__ import annotations

import hashlib
import importlib.metadata
import json
from pathlib import Path

from cpgf.version import (
    RETRIEVAL_PLANNER_VERSION,
    ROUTER_VERSION,
    SEMANTIC_CANDIDATE_VERSION,
)

MANIFEST = Path("data/manifests/semantic_candidate_b_1_0_0.json")
MEASUREMENT = Path("data/manifests/semantic_architecture_experiment_measurement_1_0_1.json")
PROVIDER = Path("src/cpgf/ai/semantic_experiment.py")
PLANNER = Path("src/cpgf/ai/retrieval_planner.py")
ROUTER = Path("src/cpgf/ai/router.py")


def _git_blob_sha(path: Path) -> str:
    content = path.read_bytes()
    header = f"blob {len(content)}\0".encode()
    return hashlib.sha1(header + content).hexdigest()


def test_semantic_candidate_b_is_frozen_before_jh5_authoring() -> None:
    p = json.loads(MANIFEST.read_text(encoding="utf-8"))

    assert p["version"] == SEMANTIC_CANDIDATE_VERSION == "1.0.0"
    assert p["status"] == "CANDIDATE_FROZEN_BEFORE_JH5_AUTHORING"
    assert p["selection_provenance"]["selected_architecture"] == "B_llm_route"
    assert p["selection_provenance"]["selection_is_not_generalization_evidence"] is True

    candidate = p["candidate"]
    assert candidate["model"] == "gpt-4o-mini-2024-07-18"
    assert candidate["model_is_snapshot"] is True
    assert candidate["openai_sdk_version"] == "3.1.0"
    assert importlib.metadata.version("openai") == "3.1.0"
    assert candidate["python_version"] == "3.12"
    assert candidate["llm_repetitions"] == 3
    assert candidate["llm_decides_route"] is True
    assert candidate["llm_decides_filters"] is False
    assert candidate["external_tools_enabled"] is False
    assert candidate["retriever_enabled"] is False
    assert candidate["llm_produces_final_answer"] is False


def test_candidate_freezes_selected_sources_and_measurement_provenance() -> None:
    p = json.loads(MANIFEST.read_text(encoding="utf-8"))

    assert p["selection_provenance"]["source_measurement_manifest_git_blob_sha"] == _git_blob_sha(
        MEASUREMENT
    )
    assert p["route_contract"]["provider_source_git_blob_sha"] == _git_blob_sha(PROVIDER)
    assert p["deterministic_planner"]["source_git_blob_sha"] == _git_blob_sha(PLANNER)
    assert p["route_type_dependency"]["router_source_git_blob_sha"] == _git_blob_sha(ROUTER)
    assert p["deterministic_planner"]["version"] == RETRIEVAL_PLANNER_VERSION == "1.3.0"
    assert p["route_type_dependency"]["router_version"] == ROUTER_VERSION == "1.4.0"


def test_jh5_design_and_acceptance_gate_are_prospective() -> None:
    p = json.loads(MANIFEST.read_text(encoding="utf-8"))
    design = p["prospective_jh5_design"]
    gate = p["prospective_jh5_acceptance_gate"]
    governance = p["governance"]

    assert design["cases"] == 48
    assert design["category_balance"] == {
        "normative": 12,
        "methodology": 12,
        "cross_source": 12,
        "control_external": 12,
    }
    assert design["expected_route_balance"] == {
        "knowledge": 24,
        "methodology": 12,
        "composite": 12,
    }
    assert design["exact_question_overlap_with_all_prior_benchmarks_allowed"] == 0
    assert design["maximum_sequence_matcher_similarity_to_any_prior_question"] == 0.70
    assert design["candidate_outputs_may_not_be_used_during_question_authoring"] is True
    assert design["candidate_may_not_execute_until_jh5_freeze_and_preflight_pass"] is True

    assert gate["minimum_B_mean_joint_exact_rate"] == 0.50
    assert gate["minimum_B_absolute_joint_gain_over_A"] == 0.10
    assert gate["minimum_B_mean_route_exact_rate"] == 0.75
    assert gate["minimum_B_mean_modal_stability"] == 0.90
    assert gate["minimum_each_category_B_mean_joint_exact_rate"] == 0.25
    assert gate["schema_violations_allowed"] == 0
    assert gate["all_criteria_required_for_broad_generalization_gate"] is True
    assert gate["thresholds_are_project_governance_not_significance_tests"] is True

    assert governance["production_activation"] is False
    assert governance["no_retriever_evaluation_before_jh5_candidate_gate"] is True
    assert governance["jh5_failure_must_be_preserved"] is True
