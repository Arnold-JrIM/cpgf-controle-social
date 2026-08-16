import json
from pathlib import Path

MANIFEST = Path("data/manifests/joint_retrieval_flow_attribution_v3_1_0_0.json")


def _manifest() -> dict[str, object]:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def test_jh3_attribution_historical_manifest_preserves_source_measurement() -> None:
    manifest = _manifest()
    source = manifest["source_independent_measurement"]

    assert manifest["status"] == "POST_HOC_DIAGNOSTIC_FROZEN"
    assert manifest["version"] == "1.0.0"
    assert source["joint_holdout_version"] == "3.0.0"
    assert source["joint_exact"] == 27
    assert source["joint_failures"] == 21
    assert source["holdout_already_known_before_this_diagnostic"] is True


def test_jh3_attribution_historical_manifest_preserves_frozen_flow() -> None:
    frozen = _manifest()["frozen_flow"]

    assert frozen["router_version"] == "1.3.0"
    assert frozen["router_source_git_blob_sha"] == (
        "7c82b42f4409110371dcb86e15672a328a0d54bd"
    )
    assert frozen["retrieval_planner_version"] == "1.2.0"
    assert frozen["retrieval_planner_source_git_blob_sha"] == (
        "7ee30359cb4457b0bd1a12b43d14f73be410ddaa"
    )


def test_jh3_attribution_historical_results_remain_frozen() -> None:
    result = _manifest()["results"]

    assert result["cases"] == 48
    assert result["actual_joint_exact"] == 27
    assert result["actual_joint_failures"] == 21
    assert result["attribution_counts"] == {
        "pass": 27,
        "planner_only": 4,
        "router_and_planner": 5,
        "router_only": 12,
    }
    assert result["router_only_failures"] == 12
    assert result["planner_only_failures"] == 4
    assert result["shared_router_planner_failures"] == 5
    assert result["router_contribution_to_joint_failures"] == 17
    assert result["planner_contribution_to_joint_failures"] == 9
    assert result["best_case_joint_exact_with_expected_route_correction_only"] == 39
    assert result["best_case_joint_exact_rate_with_expected_route_correction_only"] == 0.8125
    assert result["observed_layer_mismatch_reproduction"] == {
        "route_wrong_filters_exact": 6,
        "route_exact_filters_wrong": 4,
        "route_wrong_filters_wrong": 11,
        "clean_passes": 27,
    }


def test_jh3_attribution_historical_evidence_is_reproducible() -> None:
    evidence = _manifest()["diagnostic_evidence"]

    assert evidence["workflow_run_id"] == 31973728073
    assert evidence["python_outputs_byte_identical"] is True
    assert evidence["output_json_sha256_both"] == (
        "47bcdb1c66b2b83491ce6dd3c0abb1c0134ede4a0076926a5f3150b84d9c8d36"
    )


def test_jh3_attribution_historical_governance_remains_explicit() -> None:
    governance = _manifest()["governance"]

    assert governance["diagnostic_is_post_hoc"] is True
    assert governance["joint_holdout_3_used_as_new_independent_test"] is False
    assert governance["first_independent_measurement_preserved"] is True
    assert governance["tuning_performed_in_increment"] is False
    assert governance["not_a_new_generalization_claim"] is True
    assert governance["future_tuning_on_jh3_requires_new_independent_holdout"] is True
    assert governance["llm_called"] is False
    assert governance["sql_executed"] is False
    assert governance["retriever_called"] is False
    assert governance["external_embeddings_called"] is False
    assert governance["llm_activation_remains_blocked"] is True
