import json
from pathlib import Path

MANIFEST = Path("data/manifests/joint_retrieval_holdout_2_0_0.json")


def test_joint_holdout_v2_preserves_first_independent_measurement() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    measurement = manifest["measurement"]
    result = measurement["first_valid_measurement_result"]

    assert manifest["status"] == "MEASURED_INDEPENDENT"
    assert measurement["first_valid_measurement_run_id"] == 31967548985
    assert measurement["first_valid_measurement_head_sha"] == (
        "662cdee4c54c04f082647e640b9e4822019e209a"
    )
    assert measurement["first_valid_measurement_job_id"] == 95214916177
    assert measurement["first_valid_measurement_artifact_id"] == 9268901430
    assert measurement["first_valid_measurement_artifact_digest"] == (
        "sha256:22c426db9f28cec1e07f13ef09b3a1c92992655fdc323565032e93cc2e7a2ea2"
    )

    assert result == {
        "cases": 40,
        "route_exact": 13,
        "route_exact_rate": 0.325,
        "scope_exact": 26,
        "scope_exact_rate": 0.65,
        "temporal_exact": 24,
        "temporal_exact_rate": 0.6,
        "joint_exact": 12,
        "joint_exact_rate": 0.3,
        "mean_scope_recall": 0.7625,
        "mean_scope_precision": 0.8375,
        "mean_temporal_recall": 0.7125,
        "mean_temporal_precision": 0.825,
    }


def test_joint_holdout_v2_preserves_category_failures_without_tuning() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    by_category = manifest["measurement"]["by_category"]

    assert by_category["normative"]["joint_exact"] == 7
    assert by_category["methodology"]["joint_exact"] == 2
    assert by_category["cross_source"]["joint_exact"] == 1
    assert by_category["control_external"]["joint_exact"] == 2
    assert len(manifest["measurement"]["mismatch_ids"]["joint"]) == 28


def test_joint_holdout_v2_python_312_reproduces_first_measurement() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    reproduction = manifest["measurement"]["python_3_12_reproduction"]

    assert reproduction["job_id"] == 95214997173
    assert reproduction["artifact_id"] == 9268909720
    assert reproduction["artifact_digest"] == (
        "sha256:54daecc256c82f32065c0b926c5feeebc9b5ea8c2b6703c5b6eaacee9ef703eb"
    )
    assert reproduction["summary_exactly_matches_python_3_11"] is True
    assert reproduction["by_category_exactly_matches_python_3_11"] is True
    assert reproduction["route_confusion_exactly_matches_python_3_11"] is True
    assert reproduction["mismatch_ids_exactly_match_python_3_11"] is True


def test_joint_holdout_v2_blocks_production_claim_after_independent_measurement() -> None:
    governance = json.loads(MANIFEST.read_text(encoding="utf-8"))["governance"]

    assert governance["new_generalization_evidence_observed"] is True
    assert governance["independent_measurement_preserved_without_tuning"] is True
    assert governance["holdout_becomes_known_after_first_measurement"] is True
    assert governance["production_readiness_supported_by_this_measurement"] is False
    assert governance["llm_activation_blocked"] is True
    assert governance["llm_called"] is False
    assert governance["sql_executed"] is False
