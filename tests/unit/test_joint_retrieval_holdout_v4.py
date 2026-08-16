import json
from pathlib import Path

from cpgf.benchmark.joint_retrieval_v4 import (
    joint_holdout_v4_sha256,
    load_joint_retrieval_holdout_v4,
    validate_joint_holdout_v4_against_catalog,
    validate_joint_holdout_v4_novelty,
)
from cpgf.version import JOINT_RETRIEVAL_HOLDOUT_V4_VERSION

BENCHMARK = Path("data/benchmarks/joint_retrieval_holdout_v4_0_0.csv")
MANIFEST = Path("data/manifests/joint_retrieval_holdout_4_0_0.json")
CATALOG = Path("data/knowledge/source_catalog.json")
PRIOR = (
    Path("data/benchmarks/knowledge_retrieval_v1_0_0.csv"),
    Path("data/benchmarks/retrieval_planner_holdout_v1_0_0.csv"),
    Path("data/benchmarks/assistant_v1_0_0.csv"),
    Path("data/benchmarks/assistant_router_holdout_v1_0_0.csv"),
    Path("data/benchmarks/assistant_router_holdout_v2_0_0.csv"),
    Path("data/benchmarks/joint_retrieval_holdout_v2_0_0.csv"),
    Path("data/benchmarks/joint_retrieval_holdout_v3_0_0.csv"),
)


def _manifest() -> dict[str, object]:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def test_jh4_structure_catalog_and_novelty_are_frozen() -> None:
    suite = load_joint_retrieval_holdout_v4(BENCHMARK)
    assert JOINT_RETRIEVAL_HOLDOUT_V4_VERSION == suite.version == "4.0.0"

    catalog = validate_joint_holdout_v4_against_catalog(suite, CATALOG)
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

    novelty = validate_joint_holdout_v4_novelty(
        suite,
        PRIOR,
        max_similarity_allowed=0.75,
    )
    assert novelty["prior_questions_compared"] == 278
    assert novelty["normalized_exact_overlap"] == 0
    assert novelty["highest_sequence_similarity"] <= 0.75


def test_jh4_manifest_freezes_benchmark_flow_and_candidate_evidence() -> None:
    manifest = _manifest()
    assert manifest["version"] == "4.0.0"
    assert manifest["status"] == "FROZEN_BEFORE_MEASUREMENT"
    assert manifest["benchmark"]["sha256"] == joint_holdout_v4_sha256(BENCHMARK)
    assert manifest["benchmark"]["sha256"] == (
        "a90867717d73407b586cee02ec2eeb8c075db2f86c345bb9985193e0ca31700a"
    )

    novelty = manifest["novelty"]
    assert novelty["prospective_max_similarity"] == 0.75
    assert novelty["prior_questions_compared"] == 278
    assert novelty["normalized_exact_overlap"] == 0
    assert novelty["highest_sequence_similarity"] == 0.6648648648648648
    evidence = novelty["candidate_preflight"]
    assert evidence["run_id"] == 31976636561
    assert evidence["python_3_11"]["job_id"] == 95237014614
    assert evidence["python_3_12"]["job_id"] == 95237014509
    assert evidence["python_outputs_byte_identical"] is True
    assert evidence["router_or_planner_called"] is False

    frozen = manifest["frozen_flow"]
    assert frozen["router_version"] == "1.4.0"
    assert frozen["router_source_git_blob_sha"] == (
        "89150b97e9c87d9af0d0b0f888870dcc74ef86b1"
    )
    assert frozen["retrieval_planner_version"] == "1.3.0"
    assert frozen["retrieval_planner_source_git_blob_sha"] == (
        "8fa1458c11eeabfdde155635b74a9b770e9960c1"
    )
    assert frozen["knowledge_version"] == "1.2.0"


def test_jh4_success_criteria_are_prospective_and_non_destructive() -> None:
    manifest = _manifest()
    criteria = manifest["prospective_success_criteria"]
    assert criteria["defined_before_first_measurement"] is True
    assert criteria["primary_metric"] == "joint_route_scope_temporal_exact_rate"
    assert criteria["primary_joint_exact_target"] == 0.70
    assert criteria["route_exact_floor"] == 0.80
    assert criteria["filter_joint_exact_floor"] == 0.75
    assert criteria["per_category_joint_exact_floor"] == 0.50
    assert criteria["performance_threshold_causes_measurement_workflow_failure"] is False
    assert criteria["measurement_must_be_preserved_even_below_thresholds"] is True
    assert criteria["meeting_criteria_supports_next_retriever_evaluation_only"] is True
    assert criteria["meeting_criteria_does_not_support_production_readiness"] is True
    assert criteria["meeting_criteria_does_not_unlock_llm"] is True

    measurement = manifest["measurement"]
    assert measurement["performed"] is False
    assert measurement["first_valid_measurement"] is None
    assert measurement["result"] is None

    governance = manifest["governance"]
    assert governance["benchmark_semantics_frozen"] is True
    assert governance["all_oracles_defined_before_model_execution"] is True
    assert governance["router_or_planner_called_during_candidate_preflight"] is False
    assert governance["measurement_allowed_in_this_pr"] is False
    assert governance["first_measurement_requires_separate_post_merge_pr"] is True
    assert governance["production_readiness_supported"] is False
    assert governance["llm_activation_allowed"] is False
