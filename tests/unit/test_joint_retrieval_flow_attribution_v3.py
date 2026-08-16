from pathlib import Path

from cpgf.benchmark.joint_retrieval_attribution_v3 import (
    evaluate_joint_retrieval_flow_attribution_v3,
)
from cpgf.benchmark.joint_retrieval_v3 import load_joint_retrieval_holdout_v3

HOLDOUT = Path("data/benchmarks/joint_retrieval_holdout_v3_0_0.csv")


def _result() -> dict[str, object]:
    suite = load_joint_retrieval_holdout_v3(HOLDOUT)
    return evaluate_joint_retrieval_flow_attribution_v3(suite)


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

    assert set(counts) <= {
        "pass",
        "router_only",
        "planner_only",
        "router_and_planner",
    }
    assert sum(counts.values()) == 48
    assert counts.get("pass", 0) == 27
    assert (
        result["router_only_failures"]
        + result["planner_only_failures"]
        + result["shared_router_planner_failures"]
        == 21
    )


def test_jh3_attribution_contribution_identity() -> None:
    result = _result()

    router = result["router_contribution_to_joint_failures"]
    planner = result["planner_contribution_to_joint_failures"]
    shared = result["shared_router_planner_failures"]
    assert router + planner - shared == 21


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
