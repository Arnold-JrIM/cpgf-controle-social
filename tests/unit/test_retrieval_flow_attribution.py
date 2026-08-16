import json
from pathlib import Path

from cpgf.benchmark import (
    benchmark_sha256,
    evaluate_retrieval_flow_attribution,
    load_retrieval_benchmark,
)

HOLDOUT = Path("data/benchmarks/retrieval_planner_holdout_v1_0_0.csv")
MANIFEST = Path("data/manifests/retrieval_flow_attribution_1_0_0.json")


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


def test_frozen_attribution_manifest_matches_reproducible_diagnostic() -> None:
    suite = load_retrieval_benchmark(HOLDOUT)
    result = evaluate_retrieval_flow_attribution(suite)
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))

    assert manifest["version"] == "1.0.0"
    assert manifest["holdout"]["sha256"] == benchmark_sha256(HOLDOUT)
    assert manifest["results"]["attribution_counts"] == result["attribution_counts"]
    assert manifest["results"]["ids_by_attribution"] == result["ids_by_attribution"]
    assert manifest["results"]["actual_joint_filter_failures"] == result[
        "joint_filter_failures"
    ]
    assert manifest["results"]["router_contribution_to_joint_failures"] == result[
        "router_contribution_to_joint_failures"
    ]
    assert manifest["results"]["planner_contribution_to_joint_failures"] == result[
        "planner_contribution_to_joint_failures"
    ]
