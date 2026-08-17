from __future__ import annotations

import csv
from pathlib import Path

from cpgf.ai.contracts import ToolName
from cpgf.ai.evidence_contracts import EvidenceSource
from cpgf.benchmark.orchestration_holdout_v1 import (
    ORCHESTRATION_HOLDOUT_VERSION,
    OrchestrationHoldoutCategory,
    load_orchestration_holdout,
    orchestration_holdout_sha256,
    validate_orchestration_holdout_capabilities,
    validate_orchestration_holdout_novelty,
)

BENCHMARK = Path("data/benchmarks/orchestration_holdout_v1_0_0.csv.gz")
EXPECTED_SHA256 = "9ef3d9ac59dc16eb6762f2ae2fd7672a2305c4854614f1e5a71ef893e5d525ef"


def test_loads_balanced_prospective_suite():
    suite = load_orchestration_holdout(BENCHMARK)
    assert suite.version == ORCHESTRATION_HOLDOUT_VERSION == "1.0.0"
    assert len(suite.cases) == 56
    assert [case.id for case in suite.cases] == [f"OH1-{index:03d}" for index in range(1, 57)]

    counts = {category.value: 0 for category in OrchestrationHoldoutCategory}
    for case in suite.cases:
        counts[case.category.value] += 1
    assert counts == {category.value: 8 for category in OrchestrationHoldoutCategory}


def test_source_sets_cover_all_nonempty_combinations():
    suite = load_orchestration_holdout(BENCHMARK)
    observed = {tuple(source.value for source in case.expected_sources) for case in suite.cases}
    assert observed == {
        ("data",),
        ("knowledge",),
        ("web",),
        ("data", "knowledge"),
        ("knowledge", "web"),
        ("data", "web"),
        ("data", "knowledge", "web"),
    }


def test_capability_oracles_are_balanced_and_executable():
    suite = load_orchestration_holdout(BENCHMARK)
    result = validate_orchestration_holdout_capabilities(suite)

    assert result["status"] == "PASS"
    assert result["cases"] == 56
    assert result["source_presence_counts"] == {"data": 32, "knowledge": 32, "web": 32}
    assert result["data_cases"] == 32
    assert result["knowledge_cases"] == 32
    assert result["web_cases"] == 32
    assert result["web_official_only_cases"] == 32
    assert result["web_explicit_freshness_window_cases"] == 32
    assert result["data_tool_counts"] == {
        "overview": 7,
        "territorial_metric": 3,
        "territorial_ug_context": 3,
        "top_suppliers": 8,
        "top_ugs": 5,
        "trail_prevalence": 6,
    }


def test_data_and_web_contracts_are_explicit():
    suite = load_orchestration_holdout(BENCHMARK)
    for case in suite.cases:
        if EvidenceSource.DATA in case.expected_sources:
            assert case.expected_data_tool is not None
            assert case.expected_data_tool is not ToolName.METHODOLOGY
            assert case.expected_data_parameters
        if EvidenceSource.WEB in case.expected_sources:
            params = {parameter.name: parameter.value for parameter in case.expected_web_parameters}
            assert params["official_only"] is True
            assert isinstance(params["max_age_days"], int)
            assert 1 <= params["max_age_days"] <= 3650


def test_frozen_artifact_hash():
    assert orchestration_holdout_sha256(BENCHMARK) == EXPECTED_SHA256


def test_novelty_gate_rejects_exact_normalized_overlap(tmp_path: Path):
    suite = load_orchestration_holdout(BENCHMARK)
    prior = tmp_path / "prior.csv"
    with prior.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["id", "question"])
        writer.writeheader()
        writer.writerow({"id": "old", "question": suite.cases[0].question.upper()})

    try:
        validate_orchestration_holdout_novelty(suite, [prior], max_similarity_allowed=1.0)
    except ValueError as exc:
        assert "repetição exata normalizada" in str(exc)
    else:
        raise AssertionError("A sobreposição exata normalizada deveria ser rejeitada")
