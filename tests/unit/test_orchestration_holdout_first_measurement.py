from __future__ import annotations

import gzip
import hashlib
import json
from pathlib import Path

import pytest

from cpgf.version import ORCHESTRATION_HOLDOUT_RESULT_VERSION

RESULT = Path("data/manifests/orchestration_holdout_first_measurement_1_0_0.json")
EVIDENCE = Path("data/evidence/orchestration_holdout_v1_first_measurement_1_0_0.json.gz")

RAW_SHA256 = "d2213529f505e9d566ab64f1f27aa412e14a348abf997dfdb3d868edbab8c4c5"
GZIP_SHA256 = "ee960b344f5c0cfe796300983bdebd0d1552cf7ee8dc7b7aa400b9573128a54b"


def _load_result() -> dict[str, object]:
    return json.loads(RESULT.read_text(encoding="utf-8"))


def _raw_payload() -> tuple[bytes, dict[str, object]]:
    compressed = EVIDENCE.read_bytes()
    assert hashlib.sha256(compressed).hexdigest() == GZIP_SHA256
    raw = gzip.decompress(compressed)
    assert hashlib.sha256(raw).hexdigest() == RAW_SHA256
    return raw, json.loads(raw.decode("utf-8"))


def test_first_measurement_evidence_is_exactly_preserved():
    raw, payload = _raw_payload()
    result = _load_result()

    assert len(raw) == 476264
    assert EVIDENCE.stat().st_size == 33697
    assert payload["status"] == "INDEPENDENT_OH1_FIRST_MEASUREMENT"
    assert payload["run_context"] == {
        "github_event_name": "push",
        "github_ref": "refs/heads/main",
        "github_run_attempt": "1",
        "github_run_id": "32046979526",
        "github_sha": "ec87579fe285ddaf29b64bd05e3055ec3cb95736",
        "github_workflow": "orchestration-holdout-v1-measurement",
    }
    artifact = result["official_measurement"]["artifact"]
    assert artifact["raw_json_sha256"] == RAW_SHA256
    assert artifact["repository_gzip_sha256"] == GZIP_SHA256
    assert artifact["zip_digest"] == (
        "sha256:9626908d1c5ca5060a9067a85735d770cdc9c85003943b89b9d08f068e150222"
    )


def test_first_measurement_metrics_and_gate_are_frozen_without_relaxation():
    _, payload = _raw_payload()
    result = _load_result()
    aggregate = payload["evaluation"]["aggregate"]
    gate = payload["prospective_gate"]

    assert ORCHESTRATION_HOLDOUT_RESULT_VERSION == "1.0.0"
    assert result["version"] == ORCHESTRATION_HOLDOUT_RESULT_VERSION
    assert result["status"] == "MEASURED_INDEPENDENT_GATE_FAIL"
    assert payload["benchmark"]["cases"] == 56
    assert payload["candidate"]["model_requested"] == "gpt-4o-mini"
    assert payload["evaluation"]["response_models"] == {
        "gpt-4o-mini-2024-07-18": 161
    }
    assert payload["evaluation"]["requested_repetitions"] == 3
    assert aggregate["llm_attempts"] == 168
    assert len(payload["evaluation"]["rows"]) == 168
    assert aggregate["mean_source_set_exact_rate"] == pytest.approx(0.8392857142857143)
    assert aggregate["mean_source_precision"] == pytest.approx(0.9047619047619048)
    assert aggregate["mean_source_recall"] == pytest.approx(0.9434523809523809)
    assert aggregate["mean_data_tool_exact_rate"] == pytest.approx(0.9375)
    assert aggregate["mean_data_arguments_exact_rate"] == pytest.approx(0.9375)
    assert aggregate["mean_knowledge_filters_joint_exact_rate"] == pytest.approx(0.0)
    assert aggregate["mean_web_parameters_exact_rate"] == pytest.approx(0.53125)
    assert aggregate["mean_full_plan_exact_rate"] == pytest.approx(0.2261904761904762)
    assert payload["evaluation"]["stability"]["mean_modal_share"] == pytest.approx(
        0.494047619047619
    )
    assert aggregate["schema_violations"] == 9
    assert aggregate["provider_failures"] == 7
    assert aggregate["plan_failures"] == 2

    assert gate["passed"] is False
    assert gate["interpretation"].startswith("FAIL no gate prospectivo")
    failed = {name for name, passed in gate["checks"].items() if not passed}
    assert failed == {
        "minimum_each_category_source_set_exact_rate",
        "minimum_knowledge_filters_joint_exact_rate",
        "minimum_mean_modal_stability",
        "minimum_web_parameters_exact_rate",
        "zero_schema_violations",
    }
    assert gate["category_checks"]["data_web"] is False
    assert sum(bool(value) for value in gate["checks"].values()) == 6
    assert len(gate["checks"]) == 11


def test_result_manifest_preserves_independence_boundary():
    result = _load_result()
    governance = result["governance"]

    assert result["official_measurement"]["run_id"] == 32046979526
    assert result["official_measurement"]["job_id"] == 95437042301
    assert result["official_measurement"]["main_sha"] == (
        "ec87579fe285ddaf29b64bd05e3055ec3cb95736"
    )
    assert result["official_measurement"]["conclusion"] == "success"
    assert governance["first_measurement_is_official_independent_measurement"] is True
    assert governance["result_frozen_before_post_hoc_tuning"] is True
    assert governance["gate_not_relaxed_post_hoc"] is True
    assert governance["oh1_is_known_after_official_measurement"] is True
    assert governance["same_oh1_cannot_support_new_independence_claim_after_tuning"] is True
    assert governance["reruns_are_not_new_independent_measurements"] is True
    assert governance["production_activation"] is False
