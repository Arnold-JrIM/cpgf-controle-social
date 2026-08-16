import json
from pathlib import Path

MANIFEST = Path("data/manifests/joint_retrieval_flow_attribution_1_0_0.json")


def _manifest() -> dict[str, object]:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def test_joint_attribution_historical_manifest_preserves_source_measurement() -> None:
    manifest = _manifest()
    source = manifest["source_independent_measurement"]

    assert manifest["status"] == "POST_HOC_DIAGNOSTIC_FROZEN"
    assert manifest["version"] == "1.0.0"
    assert source["joint_holdout_version"] == "2.0.0"
    assert source["joint_exact"] == 12
    assert source["joint_failures"] == 28
    assert source["holdout_already_known_before_this_diagnostic"] is True


def test_joint_attribution_historical_manifest_preserves_frozen_flow() -> None:
    frozen = _manifest()["frozen_flow"]

    assert frozen["router_version"] == "1.2.0"
    assert frozen["router_source_git_blob_sha"] == (
        "f4236a7352e9b8808a22cf7d27c0efb1d4123821"
    )
    assert frozen["retrieval_planner_version"] == "1.1.0"
    assert frozen["retrieval_planner_source_git_blob_sha"] == (
        "2f5765a9ba70730b1af7f84ff4fc288eb3a2b96a"
    )


def test_joint_attribution_historical_results_remain_frozen() -> None:
    result = _manifest()["results"]

    assert result["cases"] == 40
    assert result["actual_joint_exact"] == 12
    assert result["actual_joint_failures"] == 28
    assert result["router_only_failures"] == 15
    assert result["planner_only_failures"] == 1
    assert result["shared_router_planner_failures"] == 12
    assert result["router_contribution_to_joint_failures"] == 27
    assert result["planner_contribution_to_joint_failures"] == 13
    assert result["best_case_joint_exact_with_expected_route_correction_only"] == 27
    assert result["best_case_joint_exact_rate_with_expected_route_correction_only"] == 0.675
    assert result["attribution_counts"] == {
        "pass": 12,
        "planner_only": 1,
        "router_and_planner": 12,
        "router_only": 15,
    }
    assert result["ids_by_attribution"]["planner_only"] == ["JH2-021"]


def test_joint_attribution_historical_governance_remains_explicit() -> None:
    governance = _manifest()["governance"]

    assert governance["diagnostic_is_post_hoc"] is True
    assert governance["joint_holdout_2_used_as_new_independent_test"] is False
    assert governance["first_independent_measurement_preserved"] is True
    assert governance["tuning_performed_in_increment"] is False
    assert governance["llm_called"] is False
    assert governance["sql_executed"] is False
    assert governance["retriever_called"] is False
    assert governance["external_embeddings_called"] is False
    assert governance["llm_activation_remains_blocked"] is True
