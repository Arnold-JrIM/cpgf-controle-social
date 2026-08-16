import json
from pathlib import Path

MANIFEST = Path("data/manifests/retrieval_planner_eval_1_0_0.json")


def test_retrieval_planner_evaluation_manifest_is_frozen_in_sample_evidence() -> None:
    payload = json.loads(MANIFEST.read_text(encoding="utf-8"))

    assert payload["version"] == "1.0.0"
    assert payload["retrieval_planner_version"] == "1.0.0"
    assert payload["retrieval_evaluation_version"] == "1.1.0"
    assert payload["benchmark_sha256"] == (
        "6633babe7e17f4c0fefb0523ea477a11257bad87d3c0bc258dea7db1c33c1777"
    )
    assert payload["chunks_sha256"] == (
        "43c7d61e8b963c5b8b1ad747ec24c2cdb5e464d403ea9b2b3776f19a5cb65b7c"
    )
    assert payload["local_result_file_sha256"] == (
        "b56380f54c5132de016181c01e78d72ab41c90fb09a294c03a629aa9fb4732b2"
    )
    assert payload["planner_source_git_blob_sha"] == (
        "6e6a0c7b6b1c39d1313b266f4ac7652ce69edc2f"
    )

    evaluation = payload["planner_evaluation"]
    assert evaluation["scope_exact_match_rate"] == 1.0
    assert evaluation["temporal_exact_match_rate"] == 29 / 30
    assert evaluation["joint_exact_match_rate"] == 29 / 30
    assert evaluation["mismatch_case_ids"] == ["KRET-002"]

    semantic = payload["results"]["semantic"]["runtime_governed"]
    hybrid = payload["results"]["hybrid"]["runtime_governed"]
    assert semantic["hit_rate_at_5"] == 29 / 30
    assert hybrid["hit_rate_at_5"] == 29 / 30
    assert semantic["failed_case_ids"] == ["KRET-004"]
    assert hybrid["failed_case_ids"] == ["KRET-004"]

    governance = payload["governance"]
    assert governance["runtime_planner_uses_benchmark_oracle"] is False
    assert governance["development_in_sample"] is True
    assert governance["generalization_claimed"] is False
    assert governance["planner_modified_after_first_measurement"] is False
    assert governance["new_holdout_required_before_production_policy_selection"] is True
