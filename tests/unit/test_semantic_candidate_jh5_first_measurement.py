from __future__ import annotations

import gzip
import hashlib
import json
from pathlib import Path

MANIFEST = Path("data/manifests/semantic_candidate_jh5_first_measurement_1_0_0.json")
EVIDENCE_GZ = Path("data/evidence/semantic_candidate_jh5_first_measurement_1_0_0.json.gz")

RAW_SHA256 = "b935b69b545c1e7536ac3da84e857ad9bc968932f586202b954433c369a8bcc2"
GZIP_SHA256 = "d8e8b0ebc2cf90891a4b2b923ff4ce78ae7e244ce675c5696ff4a9576836204c"


def _load_manifest() -> dict[str, object]:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def _load_raw() -> dict[str, object]:
    compressed = EVIDENCE_GZ.read_bytes()
    assert hashlib.sha256(compressed).hexdigest() == GZIP_SHA256
    raw = gzip.decompress(compressed)
    assert len(raw) == 214866
    assert hashlib.sha256(raw).hexdigest() == RAW_SHA256
    return json.loads(raw)


def test_first_independent_jh5_evidence_is_byte_frozen() -> None:
    manifest = _load_manifest()
    evidence = manifest["artifact_evidence"]

    assert manifest["status"] == "MEASURED_INDEPENDENT_GATE_FAIL"
    assert evidence["artifact_id"] == 9273637125
    assert evidence["artifact_zip_digest"] == (
        "sha256:46ac047f414946f3097feadfb1006efa3bfb89632e0dd41a955dc7f9b5699349"
    )
    assert evidence["raw_result_sha256"] == RAW_SHA256
    assert evidence["raw_result_gzip_sha256"] == GZIP_SHA256
    assert evidence["raw_result_bytes"] == 214866
    assert evidence["raw_result_gzip_bytes"] == 12247


def test_official_run_and_candidate_are_exactly_the_frozen_execution() -> None:
    manifest = _load_manifest()
    raw = _load_raw()

    assert manifest["official_run"] == {
        "branch": "main",
        "conclusion": "success",
        "event": "workflow_dispatch",
        "head_sha": "2dae7fb19a4d7fea91a0561ab85cb272193d826f",
        "job_id": 95259306590,
        "run_attempt": 1,
        "run_id": 31985351518,
        "workflow": "semantic-candidate-jh5-measurement",
    }
    assert raw["status"] == "INDEPENDENT_JH5_FIRST_MEASUREMENT"
    assert raw["run_context"]["github_run_id"] == "31985351518"
    assert raw["run_context"]["github_sha"] == manifest["official_run"]["head_sha"]
    assert raw["benchmark"]["sha256"] == manifest["benchmark"]["sha256"]
    assert raw["benchmark"]["independent_for_candidate_B_before_this_run"] is True

    candidate = raw["candidate"]
    assert candidate["name"] == "B_llm_route"
    assert candidate["model_requested"] == "gpt-4o-mini-2024-07-18"
    assert candidate["openai_sdk_version"] == "3.1.0"
    assert candidate["planner_version"] == "1.3.0"
    assert candidate["router_type_dependency_version"] == "1.4.0"

    b = raw["evaluation"]["candidate_B"]
    assert b["aggregate"]["llm_calls"] == 144
    assert len(b["rows"]) == 144
    assert b["aggregate"]["schema_violations"] == 0
    assert b["response_models"] == {"gpt-4o-mini-2024-07-18": 144}
    assert b["errors"] == []


def test_prospective_gate_is_preserved_as_fail_without_relaxation() -> None:
    manifest = _load_manifest()
    raw = _load_raw()
    gate = raw["prospective_gate"]

    assert gate["passed"] is False
    assert gate["checks"] == manifest["prospective_gate"]["checks"]
    assert sum(bool(value) for value in gate["checks"].values()) == 6
    assert gate["checks"]["minimum_B_absolute_joint_gain_over_A"] is False
    assert all(
        value
        for key, value in gate["checks"].items()
        if key != "minimum_B_absolute_joint_gain_over_A"
    )

    observed = gate["observed"]
    assert observed["A_joint_exact_rate"] == 0.5208333333333334
    assert observed["B_mean_joint_exact_rate"] == 0.6180555555555556
    assert observed["B_absolute_joint_gain_over_A"] == 0.09722222222222221
    assert observed["B_mean_route_exact_rate"] == 0.8680555555555556
    assert observed["B_mean_modal_stability"] == 0.9791666666666666
    assert observed["B_schema_violations"] == 0
    assert gate["rules"]["minimum_B_absolute_joint_gain_over_A"] == 0.10

    interpretation = manifest["interpretation"]
    assert interpretation["criteria_met_count"] == 6
    assert interpretation["criteria_total"] == 7
    assert interpretation["only_failed_criterion"] == "minimum_B_absolute_joint_gain_over_A"
    assert interpretation["shortfall_to_gain_threshold"] == 0.0027777777777777957
    assert interpretation["broad_generalization_gate_passed"] is False
    assert interpretation["retriever_evaluation_unblocked"] is False


def test_repetitions_categories_and_stability_match_raw_evidence() -> None:
    manifest = _load_manifest()
    raw = _load_raw()
    b = raw["evaluation"]["candidate_B"]

    assert [item["joint_exact_rate"] for item in b["repetition_summaries"]] == [
        0.6041666666666666,
        0.625,
        0.625,
    ]
    assert b["aggregate"]["worst_joint_exact_rate"] == 0.6041666666666666
    assert b["aggregate"]["mean_filter_joint_exact_rate"] == 0.6805555555555556
    assert b["aggregate"]["input_tokens"] == 31806
    assert b["aggregate"]["output_tokens"] == 5789

    assert b["stability"]["mean_modal_share"] == 0.9791666666666666
    assert b["stability"]["all_repetitions_identical_cases"] == 45
    assert manifest["stability"]["unstable_case_ids"] == ["JH5-003", "JH5-012", "JH5-023"]

    assert b["categories"]["cross_source"]["mean_route_exact_rate"] == 1.0
    assert b["categories"]["cross_source"]["mean_joint_exact_rate"] == 0.3333333333333333
    assert b["categories"]["control_external"]["mean_route_exact_rate"] == 1.0
    assert b["categories"]["control_external"]["mean_joint_exact_rate"] == 0.6666666666666666
    assert b["categories"]["methodology"]["mean_joint_exact_rate"] == 0.7222222222222222
    assert b["categories"]["normative"]["mean_joint_exact_rate"] == 0.75


def test_jh5_is_known_after_measurement_and_cannot_be_reused_for_independence() -> None:
    governance = _load_manifest()["governance"]
    assert governance["gate_not_relaxed_post_hoc"] is True
    assert governance["jh5_is_known_after_measurement"] is True
    assert governance["same_jh5_cannot_support_new_independence_claim_after_tuning"] is True
    assert governance["reruns_of_original_run_are_not_independent_measurements"] is True
    assert governance["production_activation"] is False
