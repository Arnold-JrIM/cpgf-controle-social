import json
from pathlib import Path

MANIFEST = Path("data/manifests/retrieval_planner_1_3_0.json")


def _manifest() -> dict[str, object]:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def test_planner_1_3_manifest_freezes_versions_and_sources() -> None:
    manifest = _manifest()
    assert manifest["version"] == "1.3.0"
    assert manifest["status"] == "KNOWN_REGRESSION_FROZEN"
    assert manifest["app_version"] == "0.21.0-dev"
    assert manifest["router_version_held_fixed"] == "1.4.0"
    assert manifest["router_source_git_blob_sha"] == (
        "89150b97e9c87d9af0d0b0f888870dcc74ef86b1"
    )
    assert manifest["planner_version"] == "1.3.0"
    assert manifest["planner_1_2_source_git_blob_sha"] == (
        "7ee30359cb4457b0bd1a12b43d14f73be410ddaa"
    )
    assert manifest["planner_1_3_source_git_blob_sha"] == (
        "8fa1458c11eeabfdde155635b74a9b770e9960c1"
    )


def test_planner_1_3_manifest_freezes_known_results() -> None:
    sets = _manifest()["known_regression_sets"]

    for key in ("development", "retrieval_planner_holdout_v1"):
        item = sets[key]
        assert item["cases"] == 30
        assert item["scope_exact"] == 30
        assert item["temporal_exact"] == 30
        assert item["joint_exact"] == 30
        assert item["joint_exact_rate"] == 1.0
        assert item["divergent_ids"] == []

    jh2 = sets["joint_holdout_v2"]
    assert jh2["cases"] == 40
    assert jh2["route_exact"] == 40
    assert jh2["scope_exact"] == 40
    assert jh2["temporal_exact"] == 40
    assert jh2["joint_exact"] == 40
    assert jh2["joint_error_ids"] == []

    jh3 = sets["joint_holdout_v3"]
    assert jh3["cases"] == 48
    assert jh3["route_exact"] == 48
    assert jh3["scope_exact"] == 48
    assert jh3["temporal_exact"] == 48
    assert jh3["joint_exact"] == 48
    assert jh3["joint_exact_rate"] == 1.0
    assert jh3["route_error_ids"] == []
    assert jh3["scope_error_ids"] == []
    assert jh3["temporal_error_ids"] == []
    assert jh3["joint_error_ids"] == []


def test_planner_1_3_manifest_preserves_baseline_and_independent_history() -> None:
    manifest = _manifest()
    baseline = manifest["baseline_before_planner_1_3"]
    assert baseline["route_exact"] == 48
    assert baseline["scope_exact"] == 41
    assert baseline["temporal_exact"] == 41
    assert baseline["joint_exact"] == 39
    assert baseline["remaining_joint_error_ids"] == [
        "JH3-003",
        "JH3-027",
        "JH3-028",
        "JH3-029",
        "JH3-030",
        "JH3-033",
        "JH3-034",
        "JH3-036",
        "JH3-037",
    ]

    first = manifest["historical_independent_evidence"]["joint_holdout_v3_first_measurement"]
    assert first["router_version"] == "1.3.0"
    assert first["planner_version"] == "1.2.0"
    assert first["route_exact"] == 31
    assert first["scope_exact"] == 35
    assert first["temporal_exact"] == 35
    assert first["joint_exact"] == 27
    assert first["independent"] is True


def test_planner_1_3_manifest_records_reproducible_evidence() -> None:
    evidence = _manifest()["tuning_evidence"]
    invalid = evidence["first_ci_attempt"]
    assert invalid["semantic_measurement_completed"] is False
    assert invalid["failure_class"] == "evaluation_harness"
    assert invalid["planner_rules_changed_after_failure"] is False

    valid = evidence["first_valid_known_regression"]
    assert valid["run_id"] == 31975986365
    assert valid["head_sha"] == "54d5376965a082054c639fd3761c4b87752b4e00"
    assert valid["python_3_11"]["job_id"] == 95235448227
    assert valid["python_3_11"]["artifact_id"] == 9271057937
    assert valid["python_3_12"]["job_id"] == 95235448149
    assert valid["python_3_12"]["artifact_id"] == 9271060224
    assert valid["python_outputs_byte_identical"] is True
    assert valid["output_json_sha256_both"] == (
        "7600790addec6b5261f54f5fd6a8b4bf119b31c635b3ba2d19d02f3b56f735b0"
    )


def test_planner_1_3_manifest_governance_is_known_regression_only() -> None:
    governance = _manifest()["governance"]
    assert governance["all_evaluation_sets_known_before_planner_1_3_tuning"] is True
    assert governance["joint_holdout_v3_used_as_known_regression"] is True
    assert governance["joint_holdout_v3_48_of_48_is_generalization_claim"] is False
    assert governance["new_generalization_claim"] is False
    assert governance["case_id_specific_rules_added"] is False
    assert governance["semantic_family_tuning_only"] is True
    assert governance["router_modified_in_increment"] is False
    assert governance["router_blob_preserved"] is True
    assert governance["llm_called"] is False
    assert governance["sql_executed"] is False
    assert governance["retriever_called"] is False
    assert governance["external_embeddings_called"] is False
    assert governance["production_readiness_supported"] is False
    assert governance["llm_activation_allowed"] is False
    assert governance["retriever_evaluation_still_separate"] is True
