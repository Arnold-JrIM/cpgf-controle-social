import hashlib
import json
from pathlib import Path

MANIFEST = Path("data/manifests/assistant_router_1_3_0.json")


def _sha256(path: str) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def test_router_v1_3_manifest_preserves_known_regression_contract() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))

    assert manifest["version"] == "1.3.0"
    assert manifest["status"] == "KNOWN_REGRESSION_FROZEN"
    assert manifest["router_version"] == "1.3.0"
    assert manifest["planner_version_held_fixed"] == "1.1.0"
    assert manifest["router_source_git_blob_sha"] == (
        "7c82b42f4409110371dcb86e15672a328a0d54bd"
    )
    assert manifest["planner_source_git_blob_sha"] == (
        "2f5765a9ba70730b1af7f84ff4fc288eb3a2b96a"
    )

    sets = manifest["known_regression_sets"]
    for key in ("development", "router_holdout_v1", "router_holdout_v2"):
        item = sets[key]
        assert item["sha256"] == _sha256(item["path"])
        assert item["exact"] == item["cases"]
        assert item["accuracy"] == 1.0

    joint = sets["joint_holdout_v2"]
    assert joint["sha256"] == _sha256(joint["path"])
    assert joint["cases"] == 40
    assert joint["route_exact"] == 40
    assert joint["route_accuracy"] == 1.0
    assert joint["filter_joint_exact_with_planner_1_1"] == 27
    assert joint["joint_route_scope_temporal_exact"] == 27
    assert joint["joint_exact_rate"] == 0.675
    assert joint["route_error_ids"] == []
    assert joint["remaining_filter_error_ids"] == [
        "JH2-003",
        "JH2-016",
        "JH2-021",
        "JH2-023",
        "JH2-025",
        "JH2-027",
        "JH2-028",
        "JH2-029",
        "JH2-030",
        "JH2-031",
        "JH2-032",
        "JH2-033",
        "JH2-034",
    ]


def test_router_v1_3_manifest_preserves_independent_history() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    history = manifest["historical_independent_evidence"]

    first = history["joint_holdout_v2_first_measurement"]
    assert first["router_version"] == "1.2.0"
    assert first["planner_version"] == "1.1.0"
    assert first["route_exact"] == 13
    assert first["joint_exact"] == 12
    assert first["joint_exact_rate"] == 0.3

    diagnostic = history["post_hoc_diagnostic_v1"]
    assert diagnostic["router_only_failures"] == 15
    assert diagnostic["planner_only_failures"] == 1
    assert diagnostic["shared_router_planner_failures"] == 12
    assert diagnostic["route_only_counterfactual_joint_exact"] == 27
    assert diagnostic["route_only_counterfactual_joint_exact_rate"] == 0.675
    assert history["historical_evidence_recomputed_with_router_1_3"] is False


def test_router_v1_3_manifest_governance_is_regression_only() -> None:
    governance = json.loads(MANIFEST.read_text(encoding="utf-8"))["governance"]

    assert governance["all_evaluation_sets_known_before_router_1_3_tuning"] is True
    assert governance["joint_holdout_v2_is_known_regression"] is True
    assert governance["new_generalization_claim"] is False
    assert governance["case_id_specific_rules_added"] is False
    assert governance["planner_modified_in_increment"] is False
    assert governance["planner_blob_preserved"] is True
    assert governance["historical_independent_measurement_preserved"] is True
    assert governance["llm_called"] is False
    assert governance["sql_executed"] is False
    assert governance["retriever_called"] is False
    assert governance["external_embeddings_called"] is False
    assert governance["llm_activation_allowed"] is False
    assert governance["next_layer_to_tune"] == "Retrieval Planner 1.2.0"
