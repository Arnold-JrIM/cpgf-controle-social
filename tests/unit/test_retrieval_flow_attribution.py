import json
from pathlib import Path

from cpgf.benchmark import benchmark_sha256

HOLDOUT = Path("data/benchmarks/retrieval_planner_holdout_v1_0_0.csv")
MANIFEST = Path("data/manifests/retrieval_flow_attribution_1_0_0.json")


def test_frozen_attribution_manifest_preserves_router_v1_1_history() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))

    assert manifest["version"] == "1.0.0"
    assert manifest["status"] == "POST_HOC_DIAGNOSTIC_FROZEN"
    assert manifest["router_version"] == "1.1.0"
    assert manifest["planner_version"] == "1.0.0"
    assert manifest["holdout"]["sha256"] == benchmark_sha256(HOLDOUT)
    assert manifest["holdout"]["already_known_before_diagnostic"] is True

    results = manifest["results"]
    assert results["cases"] == 30
    assert results["actual_joint_filter_failures"] == 16
    assert results["clean_passes"] == 7
    assert results["latent_router_issues_with_exact_filters"] == 7
    assert results["router_only_joint_failures"] == 7
    assert results["planner_only_joint_failures"] == 4
    assert results["shared_router_planner_joint_failures"] == 5
    assert results["router_contribution_to_joint_failures"] == 12
    assert results["planner_contribution_to_joint_failures"] == 9
    assert results["best_case_joint_exact_with_route_correction_only"] == 21

    assert results["ids_by_attribution"] == {
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

    assert manifest["governance"]["tuning_performed_in_increment"] is False
    assert manifest["governance"]["holdout_used_as_new_independent_test"] is False
