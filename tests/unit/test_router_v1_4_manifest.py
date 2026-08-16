import hashlib
import json
from pathlib import Path

MANIFEST = Path("data/manifests/assistant_router_1_4_0.json")


def _sha256(path: str) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def test_router_v1_4_manifest_preserves_known_regression_contract() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))

    assert manifest["version"] == "1.4.0"
    assert manifest["status"] == "KNOWN_REGRESSION_FROZEN"
    assert manifest["router_version"] == "1.4.0"
    assert manifest["planner_version_held_fixed"] == "1.2.0"
    assert manifest["router_source_git_blob_sha"] == (
        "89150b97e9c87d9af0d0b0f888870dcc74ef86b1"
    )
    assert manifest["planner_source_git_blob_sha"] == (
        "7ee30359cb4457b0bd1a12b43d14f73be410ddaa"
    )

    sets = manifest["known_regression_sets"]
    for key in ("development", "router_holdout_v1", "router_holdout_v2"):
        item = sets[key]
        assert item["sha256"] == _sha256(item["path"])
        assert item["exact"] == item["cases"]
        assert item["accuracy"] == 1.0

    jh2 = sets["joint_holdout_v2"]
    assert jh2["sha256"] == _sha256(jh2["path"])
    assert jh2["route_exact"] == 40
    assert jh2["route_error_ids"] == []

    jh3 = sets["joint_holdout_v3"]
    assert jh3["sha256"] == _sha256(jh3["path"])
    assert jh3["route_exact"] == 48
    assert jh3["route_error_ids"] == []
    assert jh3["scope_exact_with_planner_1_2"] == 41
    assert jh3["temporal_exact_with_planner_1_2"] == 41
    assert jh3["joint_route_scope_temporal_exact"] == 39
    assert jh3["joint_exact_rate"] == 0.8125
    assert jh3["remaining_joint_error_ids"] == [
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


def test_router_v1_4_manifest_preserves_independent_history() -> None:
    history = json.loads(MANIFEST.read_text(encoding="utf-8"))[
        "historical_independent_evidence"
    ]

    first = history["joint_holdout_v3_first_measurement"]
    assert first["router_version"] == "1.3.0"
    assert first["planner_version"] == "1.2.0"
    assert first["route_exact"] == 31
    assert first["joint_exact"] == 27
    assert first["joint_exact_rate"] == 0.5625
    assert first["independent"] is True

    diagnostic = history["post_hoc_diagnostic_v3"]
    assert diagnostic["router_only_failures"] == 12
    assert diagnostic["planner_only_failures"] == 4
    assert diagnostic["shared_router_planner_failures"] == 5
    assert diagnostic["route_only_counterfactual_joint_exact"] == 39
    assert diagnostic["route_only_counterfactual_joint_exact_rate"] == 0.8125
    assert history["historical_evidence_recomputed_with_router_1_4"] is False


def test_router_v1_4_manifest_records_reproducible_tuning_evidence() -> None:
    tuning = json.loads(MANIFEST.read_text(encoding="utf-8"))["tuning_history"]

    first = tuning["first_router_1_4_attempt"]
    assert first["route_exact_jh3"] == 47
    assert first["joint_exact_jh3"] == 38
    assert first["single_route_overreach"] == "JH3-044"
    assert first["case_id_specific_rule_added"] is False

    final = tuning["final_known_regression"]
    assert final["run_id"] == 31975011818
    assert final["python_3_11"]["job_id"] == 95233044288
    assert final["python_3_12"]["job_id"] == 95233044233
    assert final["python_outputs_byte_identical"] is True
    assert final["output_json_sha256_both"] == (
        "688827de31264b4e18efcc73a16b15761ed88b9cae80efc7a8890988e820fe39"
    )


def test_router_v1_4_manifest_governance_is_regression_only() -> None:
    governance = json.loads(MANIFEST.read_text(encoding="utf-8"))["governance"]

    assert governance["all_evaluation_sets_known_before_router_1_4_tuning"] is True
    assert governance["joint_holdout_v3_used_as_known_regression"] is True
    assert governance["joint_holdout_v3_39_of_48_is_generalization_claim"] is False
    assert governance["new_generalization_claim"] is False
    assert governance["case_id_specific_rules_added"] is False
    assert governance["semantic_family_tuning_only"] is True
    assert governance["planner_modified_in_increment"] is False
    assert governance["planner_blob_preserved"] is True
    assert governance["llm_called"] is False
    assert governance["sql_executed"] is False
    assert governance["retriever_called"] is False
    assert governance["external_embeddings_called"] is False
    assert governance["production_readiness_supported"] is False
    assert governance["llm_activation_allowed"] is False
    assert governance["next_layer_to_tune"] == "Retrieval Planner 1.3.0"
