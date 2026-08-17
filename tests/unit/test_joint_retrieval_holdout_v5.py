import hashlib
import json
from pathlib import Path

from cpgf.benchmark.joint_retrieval_v5 import (
    joint_holdout_v5_sha256,
    load_joint_retrieval_holdout_v5,
    prior_question_benchmark_paths,
    validate_joint_holdout_v5_against_catalog,
    validate_joint_holdout_v5_novelty,
)
from cpgf.version import JOINT_RETRIEVAL_HOLDOUT_V5_VERSION

BENCHMARK = Path("data/benchmarks/joint_retrieval_holdout_v5_0_0.csv")
BENCHMARK_DIR = Path("data/benchmarks")
MANIFEST = Path("data/manifests/joint_retrieval_holdout_5_0_0.json")
CANDIDATE_MANIFEST = Path("data/manifests/semantic_candidate_b_1_0_0.json")
CATALOG = Path("data/knowledge/source_catalog.json")
PROVIDER = Path("src/cpgf/ai/semantic_experiment.py")
PLANNER = Path("src/cpgf/ai/retrieval_planner.py")
ROUTER = Path("src/cpgf/ai/router.py")


def _git_blob_sha(path: Path) -> str:
    content = path.read_bytes()
    return hashlib.sha1(f"blob {len(content)}\0".encode() + content).hexdigest()


def _manifest() -> dict[str, object]:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def test_jh5_structure_catalog_and_novelty_contract() -> None:
    suite = load_joint_retrieval_holdout_v5(BENCHMARK)
    assert JOINT_RETRIEVAL_HOLDOUT_V5_VERSION == suite.version == "5.0.0"

    catalog = validate_joint_holdout_v5_against_catalog(suite, CATALOG)
    assert catalog["cases"] == 48
    assert catalog["category_counts"] == {
        "normative": 12,
        "methodology": 12,
        "cross_source": 12,
        "control_external": 12,
    }
    assert catalog["expected_route_counts"] == {
        "knowledge": 24,
        "methodology": 12,
        "composite": 12,
    }
    assert catalog["freshness_sensitive_cases"] == 2
    assert catalog["gold_documents"] == 33
    assert catalog["referenced_documents"] == 35

    prior = prior_question_benchmark_paths(BENCHMARK_DIR, current_path=BENCHMARK)
    novelty = validate_joint_holdout_v5_novelty(
        suite,
        prior,
        max_similarity_allowed=0.70,
    )
    assert novelty["prior_questions_compared"] == 326
    assert novelty["normalized_exact_overlap"] == 0
    assert novelty["highest_sequence_similarity"] == 0.6801346801346801
    assert novelty["highest_sequence_similarity_case"] == "JH5-014"
    assert novelty["highest_sequence_similarity"] <= 0.70


def test_jh5_manifest_freezes_benchmark_and_candidate_before_measurement() -> None:
    manifest = _manifest()
    assert manifest["version"] == "5.0.0"
    assert manifest["status"] == "FROZEN_BEFORE_MEASUREMENT"
    assert manifest["benchmark"]["sha256"] == joint_holdout_v5_sha256(BENCHMARK)
    assert manifest["benchmark"]["sha256"] == (
        "2695be52ff403043c394f0ca7f9f0a47f209fd2016172586146c69adf5595354"
    )

    candidate = manifest["candidate_freeze"]
    assert candidate["name"] == "B_llm_route"
    assert candidate["model"] == "gpt-4o-mini-2024-07-18"
    assert candidate["openai_sdk_version"] == "3.1.0"
    assert candidate["llm_repetitions"] == 3
    assert candidate["manifest_git_blob_sha"] == _git_blob_sha(CANDIDATE_MANIFEST)
    assert candidate["provider_source_git_blob_sha"] == _git_blob_sha(PROVIDER)
    assert candidate["retrieval_planner_source_git_blob_sha"] == _git_blob_sha(PLANNER)
    assert candidate["route_type_dependency_router_blob_sha"] == _git_blob_sha(ROUTER)
    assert candidate["candidate_executed_during_authoring"] is False
    assert candidate["candidate_executed_during_preflight"] is False


def test_jh5_clean_preflight_evidence_is_frozen() -> None:
    observed = _manifest()["novelty"]["observed_preflight"]
    assert observed["run_id"] == 31983949246
    assert observed["evidence_head_sha"] == "f014aa62ad8793bdaeae50be13db2b7c22f410e5"
    assert observed["python_3_11_job_id"] == 95255571480
    assert observed["python_3_12_job_id"] == 95255571479
    assert observed["python_3_11_artifact_id"] == 9273192096
    assert observed["python_3_12_artifact_id"] == 9273201495
    assert observed["preflight_json_bytes"] == 3849
    assert observed["preflight_json_sha256"] == (
        "4a1ac8eb94682c03bcfb7f40e8e2ff1281ebbe768cf6ff7510c22aaaa6c69c66"
    )
    assert observed["python_outputs_byte_identical"] is True
    assert observed["prior_benchmarks_compared"] == 8
    assert observed["prior_questions_compared"] == 326
    assert observed["normalized_exact_overlap"] == 0
    assert observed["highest_sequence_similarity"] == 0.6801346801346801
    assert observed["highest_sequence_similarity_case"] == "JH5-014"
    assert observed["status"] == "PASS"


def test_jh5_acceptance_gate_was_defined_prospectively() -> None:
    criteria = _manifest()["prospective_acceptance_gate"]
    assert criteria["defined_before_first_measurement"] is True
    assert criteria["all_three_llm_repetitions_must_complete"] is True
    assert criteria["schema_violations_allowed"] == 0
    assert criteria["minimum_B_mean_joint_exact_rate"] == 0.50
    assert criteria["minimum_B_absolute_joint_gain_over_A"] == 0.10
    assert criteria["minimum_B_mean_route_exact_rate"] == 0.75
    assert criteria["minimum_B_mean_modal_stability"] == 0.90
    assert criteria["minimum_each_category_B_mean_joint_exact_rate"] == 0.25
    assert criteria["all_criteria_required_for_broad_generalization_gate"] is True
    assert criteria["performance_threshold_causes_measurement_workflow_failure"] is False
    assert criteria["measurement_must_be_preserved_even_below_thresholds"] is True
    assert criteria["thresholds_are_project_governance_not_significance_tests"] is True


def test_jh5_has_not_been_measured_or_used_for_tuning() -> None:
    manifest = _manifest()
    measurement = manifest["measurement"]
    assert measurement["performed"] is False
    assert measurement["first_valid_measurement"] is None
    assert measurement["result"] is None

    governance = manifest["governance"]
    assert governance["benchmark_authored_without_candidate_outputs"] is True
    assert governance["candidate_specification_frozen_before_benchmark_authoring"] is True
    assert governance["prompt_tuning_after_authoring_started_allowed"] is False
    assert governance["model_change_after_authoring_started_allowed"] is False
    assert governance["planner_change_after_authoring_started_allowed"] is False
    assert governance["llm_called_during_preflight"] is False
    assert governance["production_activation"] is False
    assert governance["jh5_failure_must_be_preserved"] is True
