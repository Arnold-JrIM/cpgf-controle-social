import hashlib
import json
from pathlib import Path

from cpgf.version import RETRIEVAL_PLANNER_VERSION, ROUTER_VERSION

MANIFEST = Path("data/manifests/assistant_router_1_2_0.json")


def _sha256(path: str) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def test_router_v1_2_manifest_is_known_regression_not_generalization() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))

    assert manifest["version"] == "1.2.0"
    assert manifest["status"] == "KNOWN_REGRESSION_FROZEN"
    assert manifest["router_version"] == ROUTER_VERSION == "1.2.0"
    assert manifest["planner_version_held_fixed"] == RETRIEVAL_PLANNER_VERSION == "1.0.0"

    regression_sets = manifest["known_regression_sets"]
    for key in ("development", "router_holdout_v1", "router_holdout_v2"):
        item = regression_sets[key]
        assert item["sha256"] == _sha256(item["path"])
        assert item["exact"] == item["cases"]
        assert item["accuracy"] == 1.0

    retrieval = regression_sets["retrieval_planner_holdout_v1"]
    assert retrieval["sha256"] == _sha256(retrieval["path"])
    assert retrieval["cases"] == 30
    assert retrieval["joint_exact"] == 21
    assert retrieval["joint_exact_rate"] == 0.7
    assert retrieval["joint_filter_failures"] == 9
    assert retrieval["router_contribution_to_joint_failures"] == 0
    assert retrieval["planner_contribution_to_joint_failures"] == 9
    assert retrieval["latent_router_issues_with_exact_filters"] == 0
    assert retrieval["attribution_counts"] == {"pass": 21, "planner": 9}
    assert retrieval["planner_failure_ids"] == [
        "KRET-102",
        "KRET-107",
        "KRET-108",
        "KRET-119",
        "KRET-120",
        "KRET-123",
        "KRET-127",
        "KRET-128",
        "KRET-129",
    ]

    governance = manifest["governance"]
    assert governance["all_evaluation_sets_known_before_router_v1_2"] is True
    assert governance["new_generalization_claim"] is False
    assert governance["case_id_specific_rules_added"] is False
    assert governance["planner_modified_in_increment"] is False
    assert governance["next_layer_to_tune"] == "Retrieval Planner 1.1.0"
