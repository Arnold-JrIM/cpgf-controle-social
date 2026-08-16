import json
from pathlib import Path

MANIFEST = Path("data/manifests/joint_retrieval_flow_attribution_v4_1_0_0.json")


def _manifest() -> dict[str, object]:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def test_jh4_attribution_historical_manifest_preserves_source_measurement() -> None:
    manifest = _manifest()
    source = manifest["source_independent_measurement"]

    assert manifest["status"] == "POST_HOC_DIAGNOSTIC_FROZEN"
    assert manifest["version"] == "1.0.0"
    assert source["joint_holdout_version"] == "4.0.0"
    assert source["joint_exact"] == 18
    assert source["joint_failures"] == 30
    assert source["holdout_already_known_before_this_diagnostic"] is True


def test_jh4_attribution_historical_manifest_preserves_frozen_flow() -> None:
    frozen = _manifest()["frozen_flow"]

    assert frozen["router_version"] == "1.4.0"
    assert frozen["router_source_git_blob_sha"] == (
        "89150b97e9c87d9af0d0b0f888870dcc74ef86b1"
    )
    assert frozen["retrieval_planner_version"] == "1.3.0"
    assert frozen["retrieval_planner_source_git_blob_sha"] == (
        "8fa1458c11eeabfdde155635b74a9b770e9960c1"
    )


def test_jh4_attribution_historical_results_remain_frozen() -> None:
    result = _manifest()["results"]

    assert result["cases"] == 48
    assert result["actual_joint_exact"] == 18
    assert result["actual_joint_failures"] == 30
    assert result["attribution_counts"] == {
        "pass": 18,
        "planner_only": 2,
        "router_and_planner": 15,
        "router_only": 13,
    }
    assert result["router_only_failures"] == 13
    assert result["planner_only_failures"] == 2
    assert result["shared_router_planner_failures"] == 15
    assert result["router_contribution_to_joint_failures"] == 28
    assert result["planner_contribution_to_joint_failures"] == 17
    assert result["best_case_joint_exact_with_expected_route_correction_only"] == 31
    assert result["best_case_joint_exact_rate_with_expected_route_correction_only"] == (
        0.6458333333333334
    )
    assert result["expected_route_filter_exact_cases"] == 31
    assert result["any_documentary_route_filter_exact_cases"] == 31
    assert result["observed_layer_mismatch_reproduction"] == {
        "route_wrong_filters_exact": 6,
        "route_exact_filters_wrong": 2,
        "route_wrong_filters_wrong": 22,
        "clean_passes": 18,
    }


def test_jh4_attribution_historical_category_pattern_remains_frozen() -> None:
    by_category = _manifest()["results"]["attribution_by_category"]

    assert by_category["methodology"] == {"pass": 5, "router_only": 7}
    assert by_category["cross_source"] == {
        "pass": 1,
        "router_and_planner": 9,
        "router_only": 2,
    }
    assert by_category["control_external"] == {
        "pass": 5,
        "planner_only": 2,
        "router_and_planner": 5,
    }
    assert by_category["normative"] == {
        "pass": 7,
        "router_and_planner": 1,
        "router_only": 4,
    }


def test_jh4_attribution_historical_evidence_is_reproducible() -> None:
    evidence = _manifest()["diagnostic_evidence"]

    assert evidence["workflow_run_id"] == 31979015958
    assert evidence["python_outputs_byte_identical"] is True
    assert evidence["output_json_sha256_both"] == (
        "6b0f4f184f846a2cf08bf603e6b254e43591ffdb0a627f1cd48a94266a7a4f2c"
    )


def test_jh4_attribution_historical_governance_remains_explicit() -> None:
    governance = _manifest()["governance"]

    assert governance["diagnostic_is_post_hoc"] is True
    assert governance["joint_holdout_4_used_as_new_independent_test"] is False
    assert governance["first_independent_measurement_preserved"] is True
    assert governance["tuning_performed_in_increment"] is False
    assert governance["not_a_new_generalization_claim"] is True
    assert (
        governance[
            "future_tuning_or_architecture_selection_on_jh4_requires_new_independent_jh5"
        ]
        is True
    )
    assert governance["llm_called"] is False
    assert governance["sql_executed"] is False
    assert governance["retriever_called"] is False
    assert governance["external_embeddings_called"] is False
    assert governance["production_llm_activation_allowed"] is False
