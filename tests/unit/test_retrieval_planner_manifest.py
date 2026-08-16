import json
from pathlib import Path

MANIFEST = Path("data/manifests/retrieval_planner_1_0_0.json")


def test_retrieval_planner_manifest_preserves_historical_freeze() -> None:
    payload = json.loads(MANIFEST.read_text(encoding="utf-8"))

    assert payload["version"] == "1.0.0"
    assert payload["status"] == "FROZEN_BEFORE_MEASUREMENT"
    assert payload["planner_source"] == "src/cpgf/ai/retrieval_planner.py"
    assert payload["planner_source_git_blob_sha"] == (
        "6e6a0c7b6b1c39d1313b266f4ac7652ce69edc2f"
    )
    assert payload["router_version"] == "1.1.0"
    assert payload["governance"]["planner_rules_must_not_change_after_first_measurement"] is True
    assert payload["governance"]["generalization_claimed"] is False
    assert payload["governance"]["new_holdout_required_before_production_policy_selection"] is True
