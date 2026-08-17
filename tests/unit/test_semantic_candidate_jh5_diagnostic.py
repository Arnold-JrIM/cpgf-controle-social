from __future__ import annotations

import json
from pathlib import Path

from cpgf.benchmark.semantic_candidate_jh5_diagnostic import (
    DIAGNOSTIC_VERSION,
    diagnose_measurement,
    diagnostic_json,
    load_measurement,
)
from cpgf.version import SEMANTIC_CANDIDATE_JH5_DIAGNOSTIC_VERSION

MEASUREMENT = Path("data/evidence/semantic_candidate_jh5_first_measurement_1_0_0.json.gz")
MANIFEST = Path("data/manifests/semantic_candidate_jh5_diagnostic_1_0_0.json")


def test_jh5_post_hoc_diagnostic_recomputes_frozen_manifest():
    observed = diagnose_measurement(load_measurement(MEASUREMENT))
    expected = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert observed == expected


def test_jh5_post_hoc_diagnostic_has_expected_error_structure():
    report = diagnose_measurement(load_measurement(MEASUREMENT))

    assert report["status"] == "POST_HOC_DIAGNOSTIC_ONLY"
    assert report["observed_repetition_level"] == {
        "rows": 144,
        "joint_passes": 89,
        "joint_failures": 55,
        "route_failures": 19,
        "filter_failures": 46,
        "scope_failures": 40,
        "temporal_failures": 40,
        "exactness_patterns": {
            "RST": 89,
            "RSt": 6,
            "RsT": 6,
            "Rst": 24,
            "rST": 9,
            "rst": 10,
        },
    }
    assert report["modal_case_level"]["class_counts"] == {
        "pass": 30,
        "route_only": 3,
        "filters_only": 12,
        "route_and_filters": 3,
    }
    cross_source = report["category_modal_summary"]["cross_source"]
    control_external = report["category_modal_summary"]["control_external"]
    assert cross_source["modal_route_exact"] == 12
    assert cross_source["modal_joint_pass"] == 4
    assert control_external["modal_route_exact"] == 12
    assert (
        report["architectural_reading"]["composite_route_recall_across_repetitions"]
        == 1.0
    )
    assert report["governance"]["no_llm_call"] is True
    assert report["governance"]["no_retriever_execution"] is True
    assert (
        report["governance"]["next_independent_evidence_requires_new_prospective_holdout"]
        is True
    )


def test_diagnostic_serialization_is_deterministic():
    measurement = load_measurement(MEASUREMENT)
    assert diagnostic_json(measurement) == MANIFEST.read_text(encoding="utf-8")


def test_diagnostic_version_contract():
    assert DIAGNOSTIC_VERSION == "1.0.0"
    assert SEMANTIC_CANDIDATE_JH5_DIAGNOSTIC_VERSION == "1.0.0"
