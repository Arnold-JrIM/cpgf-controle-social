from pathlib import Path

from cpgf.benchmark import (
    JointRetrievalFlowAttribution,
    evaluate_joint_retrieval_flow_attribution,
    load_joint_retrieval_holdout,
)

HOLDOUT = Path("data/benchmarks/joint_retrieval_holdout_v2_0_0.csv")


def _result() -> dict[str, object]:
    suite = load_joint_retrieval_holdout(HOLDOUT)
    return evaluate_joint_retrieval_flow_attribution(suite)


def test_joint_attribution_reproduces_measured_baseline() -> None:
    result = _result()

    assert result["cases"] == 40
    assert result["actual_joint_exact"] == 12
    assert result["actual_joint_failures"] == 28
    assert result["observed_layer_mismatch_reproduction"] == {
        "route_wrong_filters_exact": 9,
        "route_exact_filters_wrong": 1,
        "route_wrong_filters_wrong": 18,
        "clean_passes": 12,
    }


def test_joint_attribution_is_mutually_exclusive_and_exhaustive() -> None:
    result = _result()
    counts = result["attribution_counts"]

    assert set(counts) <= {item.value for item in JointRetrievalFlowAttribution}
    assert sum(counts.values()) == 40
    assert counts.get("pass", 0) == 12
    assert (
        counts.get("router_only", 0)
        + counts.get("planner_only", 0)
        + counts.get("router_and_planner", 0)
        == 28
    )


def test_joint_attribution_contributions_do_not_double_count_shared_cases() -> None:
    result = _result()

    router = result["router_contribution_to_joint_failures"]
    planner = result["planner_contribution_to_joint_failures"]
    shared = result["shared_router_planner_failures"]

    assert router + planner - shared == 28
    assert result["best_case_joint_exact_with_expected_route_correction_only"] == (
        12 + result["router_only_failures"]
    )


def test_each_failure_uses_expected_route_counterfactual_for_primary_attribution() -> None:
    result = _result()

    for row in result["cases_detail"]:
        attribution = row["attribution"]
        if attribution == "router_only":
            assert row["route_exact"] is False
            assert row["expected_route_counterfactual"]["filter_joint_exact"] is True
        elif attribution == "planner_only":
            assert row["route_exact"] is True
            assert row["actual_filters"]["filter_joint_exact"] is False
        elif attribution == "router_and_planner":
            assert row["route_exact"] is False
            assert row["expected_route_counterfactual"]["filter_joint_exact"] is False
        else:
            assert attribution == "pass"
            assert row["actual_joint_exact"] is True


def test_joint_attribution_preserves_governance_contract() -> None:
    result = _result()
    governance = result["governance"]

    assert governance["diagnostic_is_post_hoc"] is True
    assert governance["joint_holdout_2_is_already_known"] is True
    assert governance["first_independent_measurement_preserved"] is True
    assert governance["router_rules_modified"] is False
    assert governance["planner_rules_modified"] is False
    assert governance["question_and_oracle_held_fixed"] is True
    assert governance["counterfactual_changes_only_route_decision"] is True
    assert governance["not_a_new_generalization_claim"] is True
    assert governance["llm_called"] is False
    assert governance["sql_executed"] is False
    assert governance["retriever_called"] is False
