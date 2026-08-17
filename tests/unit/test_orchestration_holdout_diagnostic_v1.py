import hashlib
import json
from pathlib import Path

import pytest

from cpgf.benchmark.orchestration_holdout_diagnostic_v1 import (
    ORCHESTRATION_HOLDOUT_DIAGNOSTIC_VERSION,
    diagnose_measurement,
    diagnostic_json,
    load_frozen_measurement,
)

PREFIX = "orchestration_holdout_v1_first_measurement_1_0_0.json.gz.b64."
EVIDENCE_DIR = Path("data/evidence")
DIAGNOSTIC_MANIFEST = Path("data/manifests/orchestration_holdout_diagnostic_1_0_0.json")


def _parts() -> list[Path]:
    return [EVIDENCE_DIR / f"{PREFIX}{index:02d}" for index in range(8)]


def _measurement():
    return load_frozen_measurement([str(path) for path in _parts()])


def test_frozen_oh1_measurement_reconstructs_and_diagnoses_offline():
    measurement = _measurement()
    diagnostic = diagnose_measurement(measurement)

    assert ORCHESTRATION_HOLDOUT_DIAGNOSTIC_VERSION == "1.0.0"
    assert diagnostic["status"] == "POST_HOC_DIAGNOSTIC_ONLY"
    assert diagnostic["source"]["prospective_gate_passed"] is False

    repetition = diagnostic["repetition_level"]
    assert repetition["rows"] == 168
    assert repetition["source_set_exact"] == 141
    assert repetition["full_plan_exact"] == 38

    assert diagnostic["data_parameterization"]["required_rows"] == 96
    assert diagnostic["data_parameterization"]["tool_exact"] == 90
    assert diagnostic["data_parameterization"]["arguments_exact"] == 90

    knowledge = diagnostic["knowledge_parameterization"]
    assert knowledge["required_rows"] == 96
    assert knowledge["joint_exact"] == 0

    web = diagnostic["web_parameterization"]
    assert web["required_rows"] == 96
    assert web["joint_exact"] == 51

    stability = diagnostic["stability"]
    assert stability["unstable_cases"] == 47
    assert stability["component_mean_modal_share"]["full_signature"] == pytest.approx(
        0.494047619047619
    )

    failures = diagnostic["structural_and_provider_failures"]
    assert failures["schema_violations"] == 9
    assert failures["provider_failures"] == 7
    assert failures["plan_failures"] == 2

    assert diagnostic["category_summary"]["data_web"]["source_set_exact"] == 11
    assert diagnostic["governance"]["no_llm_call"] is True
    assert diagnostic["governance"]["no_prompt_or_policy_tuning"] is True
    assert diagnostic["governance"]["production_activation"] is False


def test_frozen_diagnostic_summary_matches_deterministic_output():
    measurement = _measurement()
    generated = diagnostic_json(measurement).encode("utf-8")
    manifest = json.loads(DIAGNOSTIC_MANIFEST.read_text(encoding="utf-8"))

    assert len(generated) == manifest["source"]["generated_diagnostic_size_bytes"]
    assert hashlib.sha256(generated).hexdigest() == manifest["source"][
        "generated_diagnostic_sha256"
    ]
    assert manifest["repetition_level"]["source_set_exact"] == 141
    assert manifest["repetition_level"]["full_plan_exact"] == 38
    assert manifest["knowledge_parameterization"]["joint_exact"] == 0
    assert manifest["web_parameterization"]["joint_exact"] == 51
    assert manifest["stability"]["unstable_cases"] == 47
    assert manifest["structural_and_provider_failures"]["schema_violations"] == 9


def test_diagnostic_sources_do_not_call_model_or_workers():
    for path in (
        Path("src/cpgf/benchmark/orchestration_holdout_diagnostic_v1.py"),
        Path("scripts/diagnose_orchestration_holdout_v1.py"),
    ):
        source = path.read_text(encoding="utf-8")
        for forbidden in (
            "OpenAI(",
            "OpenAIResponsesOrchestratorProvider",
            "plan_evidence(",
            "execute_tool(",
            "retrieve_knowledge_need(",
            "retrieve_web_need(",
            "duckdb.connect",
        ):
            assert forbidden not in source, (path, forbidden)
