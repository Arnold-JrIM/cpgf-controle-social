import hashlib
import json
from pathlib import Path

from cpgf.benchmark import benchmark_sha256, joint_holdout_sha256
from cpgf.version import RETRIEVAL_PLANNER_VERSION, ROUTER_VERSION

MANIFEST = Path("data/manifests/retrieval_planner_1_2_0.json")
DEVELOPMENT = Path("data/benchmarks/knowledge_retrieval_v1_0_0.csv")
KNOWN_HOLDOUT = Path("data/benchmarks/retrieval_planner_holdout_v1_0_0.csv")
JOINT_HOLDOUT = Path("data/benchmarks/joint_retrieval_holdout_v2_0_0.csv")


def _git_blob_sha(path: str) -> str:
    content = Path(path).read_bytes()
    header = f"blob {len(content)}\0".encode()
    return hashlib.sha1(header + content).hexdigest()


def test_planner_1_2_manifest_matches_current_operational_sources() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))

    assert manifest["version"] == RETRIEVAL_PLANNER_VERSION == "1.2.0"
    assert manifest["router_version"] == ROUTER_VERSION == "1.3.0"
    assert manifest["status"] == "KNOWN_REGRESSION_FROZEN"
    assert manifest["app_version"] == "0.19.0-dev"
    assert manifest["planner_1_2_source_git_blob_sha"] == _git_blob_sha(
        manifest["planner_source"]
    )
    assert manifest["router_source_git_blob_sha"] == _git_blob_sha(
        manifest["router_source"]
    )
    assert manifest["planner_1_1_source_git_blob_sha"] == (
        "2f5765a9ba70730b1af7f84ff4fc288eb3a2b96a"
    )


def test_planner_1_2_manifest_freezes_known_regression_inputs_and_results() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    sets = manifest["known_regression_sets"]

    development = sets["development"]
    known = sets["retrieval_planner_holdout_v1"]
    joint = sets["joint_holdout_v2"]

    assert development["sha256"] == benchmark_sha256(DEVELOPMENT)
    assert known["sha256"] == benchmark_sha256(KNOWN_HOLDOUT)
    assert joint["sha256"] == joint_holdout_sha256(JOINT_HOLDOUT)

    for item in (development, known):
        assert item["cases"] == 30
        assert item["scope_exact"] == 30
        assert item["temporal_exact"] == 30
        assert item["joint_exact"] == 30
        assert item["joint_exact_rate"] == 1.0
        assert item["divergent_ids"] == []

    assert joint["cases"] == 40
    assert joint["route_exact"] == 40
    assert joint["scope_exact"] == 40
    assert joint["temporal_exact"] == 40
    assert joint["filter_joint_exact"] == 40
    assert joint["joint_exact"] == 40
    assert joint["joint_exact_rate"] == 1.0
    for key in (
        "route_error_ids",
        "scope_error_ids",
        "temporal_error_ids",
        "filter_error_ids",
        "joint_error_ids",
    ):
        assert joint[key] == []


def test_planner_1_2_manifest_preserves_history_without_relabeling_generalization() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    history = manifest["historical_evolution"]

    first = history["joint_holdout_v2_first_independent_measurement"]
    assert first["router_version"] == "1.2.0"
    assert first["planner_version"] == "1.1.0"
    assert first["route_exact"] == 13
    assert first["joint_exact"] == 12
    assert first["joint_exact_rate"] == 0.3
    assert first["independent"] is True

    router = history["after_router_1_3_before_planner_1_2"]
    assert router["route_exact"] == 40
    assert router["filter_joint_exact"] == 27
    assert router["joint_exact"] == 27
    assert router["independent"] is False
    assert len(router["remaining_filter_error_ids"]) == 13

    planner = history["after_planner_1_2_known_regression"]
    assert planner["route_exact"] == 40
    assert planner["filter_joint_exact"] == 40
    assert planner["joint_exact"] == 40
    assert planner["independent"] is False


def test_planner_1_2_manifest_records_valid_ci_evidence_and_governance() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    evidence = manifest["first_valid_known_regression_evidence"]

    assert evidence["head_sha"] == "e2fc2be638598c9e8a2b79fc6706a036453e4654"
    assert evidence["run_id"] == 31970356324
    assert evidence["python_3_11"]["job_id"] == 95221772963
    assert evidence["python_3_11"]["artifact_id"] == 9269620321
    assert evidence["python_3_11"]["conclusion"] == "success"
    assert evidence["python_3_12"]["job_id"] == 95221773029
    assert evidence["python_3_12"]["artifact_id"] == 9269626299
    assert evidence["python_3_12"]["conclusion"] == "success"

    governance = manifest["governance"]
    assert governance["all_evaluation_sets_known_before_planner_1_2_tuning"] is True
    assert governance["joint_holdout_v2_used_for_planner_1_2_tuning"] is True
    assert governance["joint_holdout_v2_40_of_40_is_generalization_claim"] is False
    assert governance["new_generalization_claim"] is False
    assert governance["router_modified_in_increment"] is False
    assert governance["router_1_3_blob_preserved"] is True
    assert governance["case_id_specific_rules_added"] is False
    assert governance["planner_rules_are_deterministic"] is True
    assert governance["historical_independent_measurement_preserved"] is True
    assert governance["llm_called"] is False
    assert governance["sql_executed"] is False
    assert governance["retriever_called"] is False
    assert governance["external_embeddings_called"] is False
    assert governance["llm_activation_allowed"] is False
    assert "Joint Holdout 3.0" in governance["next_generalization_gate"]
