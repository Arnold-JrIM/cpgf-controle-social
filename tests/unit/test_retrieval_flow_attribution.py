from pathlib import Path

from cpgf.benchmark import evaluate_retrieval_flow_attribution, load_retrieval_benchmark

HOLDOUT = Path("data/benchmarks/retrieval_planner_holdout_v1_0_0.csv")


def test_retrieval_flow_attribution_decomposes_known_holdout_without_tuning() -> None:
    suite = load_retrieval_benchmark(HOLDOUT)
    result = evaluate_retrieval_flow_attribution(suite)

    assert result["cases"] == 30
    assert result["retrieval_capable_routes"] == ["knowledge", "methodology", "composite"]
    assert result["joint_filter_failures"] == 16
    assert result["attribution_counts"] == {
        "pass": 7,
        "planner": 4,
        "router_and_planner": 5,
        "router_blocking": 6,
        "router_latent": 7,
        "router_selection": 1,
    }
    assert result["router_contribution_to_joint_failures"] == 12
    assert result["planner_contribution_to_joint_failures"] == 9
    assert result["shared_router_planner_failures"] == 5
    assert result["latent_router_issues_with_exact_filters"] == 7
    assert result["clean_passes"] == 7

    assert result["ids_by_attribution"] == {
        "pass": [
            "KRET-103",
            "KRET-104",
            "KRET-106",
            "KRET-111",
            "KRET-121",
            "KRET-122",
            "KRET-124",
        ],
        "planner": ["KRET-102", "KRET-108", "KRET-120", "KRET-129"],
        "router_and_planner": [
            "KRET-107",
            "KRET-119",
            "KRET-123",
            "KRET-127",
            "KRET-128",
        ],
        "router_blocking": [
            "KRET-113",
            "KRET-115",
            "KRET-116",
            "KRET-117",
            "KRET-118",
            "KRET-126",
        ],
        "router_latent": [
            "KRET-101",
            "KRET-105",
            "KRET-109",
            "KRET-110",
            "KRET-112",
            "KRET-125",
            "KRET-130",
        ],
        "router_selection": ["KRET-114"],
    }

    assert result["governance"] == {
        "diagnostic_is_post_hoc": True,
        "holdout_is_already_known": True,
        "router_rules_modified": False,
        "planner_rules_modified": False,
        "counterfactual_changes_only_route_decision": True,
        "question_and_oracle_held_fixed": True,
        "not_a_new_generalization_claim": True,
    }
