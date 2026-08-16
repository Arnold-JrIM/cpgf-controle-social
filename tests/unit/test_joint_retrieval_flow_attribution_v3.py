import json
from pathlib import Path

from cpgf.benchmark.joint_retrieval_attribution_v3 import (
    evaluate_joint_retrieval_flow_attribution_v3,
)
from cpgf.benchmark.joint_retrieval_v3 import load_joint_retrieval_holdout_v3

HOLDOUT = Path("data/benchmarks/joint_retrieval_holdout_v3_0_0.csv")
MANIFEST = Path("data/manifests/joint_retrieval_flow_attribution_v3_1_0_0.json")


def _result() -> dict[str, object]:
    suite = load_joint_retrieval_holdout_v3(HOLDOUT)
    return evaluate_joint_retrieval_flow_attribution_v3(suite)


def _manifest() -> dict[str, object]:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def test_jh3_attribution_reproduces_independent_baseline() -> None:
    result = _result()

    assert result["cases"] == 48
    assert result["actual_joint_exact"] == 27
    assert result["actual_joint_failures"] == 21
    assert result["observed_layer_mismatch_reproduction"] == {
        "route_wrong_filters_exact": 6,
        "route_exact_filters_wrong": 4,
        "route_wrong_filters_wrong": 11,
        "clean_passes": 27,
    }


def test_jh3_attribution_is_mutually_exclusive_and_exhaustive() -> None:
    result = _result()
    counts = result["attribution_counts"]

    assert counts == {
        "pass": 27,
        "planner_only": 4,
        "router_and_planner": 5,
        "router_only": 12,
    }
    assert sum(counts.values()) == 48
    assert (
        result["router_only_failures"]
        + result["planner_only_failures"]
        + result["shared_router_planner_failures"]
        == 21
    )


def test_jh3_attribution_contribution_identity_and_counterfactual_bound() -> None:
    result = _result()

    router = result["router_contribution_to_joint_failures"]
    planner = result["planner_contribution_to_joint_failures"]
    shared = result["shared_router_planner_failures"]
    assert router == 17
    assert planner == 9
    assert shared == 5
    assert router + planner - shared == 21
    assert result["best_case_joint_exact_with_expected_route_correction_only"] == 39
    assert result["best_case_joint_exact_rate_with_expected_route_correction_only"] == 0.8125
    assert result["expected_route_filter_exact_cases"] == 39
    assert result["any_documentary_route_filter_exact_cases"] == 39


def test_jh3_expected_route_counterfactual_defines_primary_attribution() -> None:
    result = _result()

    for row in result["cases_detail"]:
        attribution = row["attribution"]
        route_exact = row["route_exact"]
        actual_filters_exact = row["actual_filters"]["filter_joint_exact"]
        expected_filters_exact = row["expected_route_counterfactual"][
            "filter_joint_exact"
        ]
        if attribution == "pass":
            assert route_exact is True
            assert actual_filters_exact is True
        elif attribution == "planner_only":
            assert route_exact is True
            assert actual_filters_exact is False
        elif attribution == "router_only":
            assert route_exact is False
            assert expected_filters_exact is True
        elif attribution == "router_and_planner":
            assert route_exact is False
            assert expected_filters_exact is False
        else:
            raise AssertionError(f"Atribuição inesperada: {attribution}")


def test_jh3_dynamic_result_matches_frozen_manifest() -> None:
    result = _result()
    frozen = _manifest()["results"]

    for key in (
        "cases",
        "actual_joint_exact",
        "actual_joint_failures",
        "attribution_counts",
        "ids_by_attribution",
        "attribution_by_category",
        "router_only_failures",
        "planner_only_failures",
        "shared_router_planner_failures",
        "router_contribution_to_joint_failures",
        "planner_contribution_to_joint_failures",
        "best_case_joint_exact_with_expected_route_correction_only",
        "best_case_joint_exact_rate_with_expected_route_correction_only",
        "expected_route_filter_exact_cases",
        "any_documentary_route_filter_exact_cases",
        "observed_layer_mismatch_reproduction",
    ):
        assert result[key] == frozen[key]


def test_jh3_frozen_manifest_preserves_evidence_and_governance() -> None:
    manifest = _manifest()
    source = manifest["source_independent_measurement"]
    evidence = manifest["diagnostic_evidence"]
    governance = manifest["governance"]

    assert manifest["status"] == "POST_HOC_DIAGNOSTIC_FROZEN"
    assert manifest["version"] == "1.0.0"
    assert source["joint_holdout_version"] == "3.0.0"
    assert source["joint_exact"] == 27
    assert source["joint_failures"] == 21
    assert evidence["python_outputs_byte_identical"] is True
    assert evidence["output_json_sha256_both"] == (
        "47bcdb1c66b2b83491ce6dd3c0abb1c0134ede4a0076926a5f3150b84d9c8d36"
    )
    assert governance["diagnostic_is_post_hoc"] is True
    assert governance["joint_holdout_3_used_as_new_independent_test"] is False
    assert governance["tuning_performed_in_increment"] is False
    assert governance["llm_activation_remains_blocked"] is True


def test_jh3_attribution_governance() -> None:
    governance = _result()["governance"]

    assert governance["diagnostic_is_post_hoc"] is True
    assert governance["joint_holdout_3_is_already_known"] is True
    assert governance["first_independent_measurement_preserved"] is True
    assert governance["router_rules_modified"] is False
    assert governance["planner_rules_modified"] is False
    assert governance["counterfactual_changes_only_route_decision"] is True
    assert governance["not_a_new_generalization_claim"] is True
    assert governance["llm_called"] is False
    assert governance["sql_executed"] is False
    assert governance["retriever_called"] is False
    assert governance["external_embeddings_called"] is False
