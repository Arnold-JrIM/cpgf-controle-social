from __future__ import annotations

import gzip
import hashlib
from pathlib import Path

import pytest

from cpgf.ai.contracts import ToolName
from cpgf.ai.evidence_contracts import EvidenceSource
from cpgf.benchmark.orchestration_holdout_v2 import (
    FROZEN_PRIOR_BENCHMARK_PATHS,
    ORCHESTRATION_HOLDOUT_V2_VERSION,
    OrchestrationHoldoutV2Category,
    load_orchestration_holdout_v2,
    normalize_question_v2,
    orchestration_holdout_v2_sha256,
    questions_from_benchmark_v2,
    validate_frozen_prior_benchmarks_v2,
    validate_orchestration_holdout_v2_capabilities,
    validate_orchestration_holdout_v2_novelty,
)

BENCHMARK = Path("data/benchmarks/orchestration_holdout_v2_0_0.csv.gz")
EXPECTED_SHA256 = "a3d1a126c7526d8be53fbeabff075792aa6734d399d03c60bd30693fdc9aa9d3"
EXPECTED_UNCOMPRESSED_SHA256 = (
    "2cc6300db90622ce35cf458aad29168a56b58a371b290abdf5de84fe76e9cc6c"
)


def test_loads_balanced_prospective_oh2_suite():
    suite = load_orchestration_holdout_v2(BENCHMARK)
    assert suite.version == ORCHESTRATION_HOLDOUT_V2_VERSION == "2.0.0"
    assert len(suite.cases) == 56
    assert [case.id for case in suite.cases] == [
        f"OH2-{index:03d}" for index in range(1, 57)
    ]

    counts = {category.value: 0 for category in OrchestrationHoldoutV2Category}
    for case in suite.cases:
        counts[case.category.value] += 1
    assert counts == {category.value: 8 for category in OrchestrationHoldoutV2Category}


def test_source_sets_cover_all_nonempty_combinations():
    suite = load_orchestration_holdout_v2(BENCHMARK)
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
    suite = load_orchestration_holdout_v2(BENCHMARK)
    result = validate_orchestration_holdout_v2_capabilities(suite)

    assert result["status"] == "PASS"
    assert result["cases"] == 56
    assert result["source_presence_counts"] == {
        "data": 32,
        "knowledge": 32,
        "web": 32,
    }
    assert result["data_cases"] == 32
    assert result["knowledge_cases"] == 32
    assert result["web_cases"] == 32
    assert result["web_official_only_cases"] == 32
    assert result["web_explicit_freshness_window_cases"] == 32
    assert result["data_tool_counts"] == {
        "overview": 6,
        "territorial_metric": 7,
        "territorial_ug_context": 4,
        "top_suppliers": 6,
        "top_ugs": 5,
        "trail_prevalence": 4,
    }


def test_data_knowledge_and_web_contracts_are_explicit():
    suite = load_orchestration_holdout_v2(BENCHMARK)
    for case in suite.cases:
        if EvidenceSource.DATA in case.expected_sources:
            assert case.expected_data_tool is not None
            assert case.expected_data_tool is not ToolName.METHODOLOGY
            assert case.expected_data_parameters

        if EvidenceSource.KNOWLEDGE in case.expected_sources:
            assert case.expected_knowledge_scopes
            assert case.expected_knowledge_temporal_statuses
            assert case.expected_knowledge_source_classes

        if EvidenceSource.WEB in case.expected_sources:
            params = {parameter.name: parameter.value for parameter in case.expected_web_parameters}
            assert params["official_only"] is True
            assert isinstance(params["max_age_days"], int)
            assert 1 <= params["max_age_days"] <= 3650
            assert 1 <= params["limit"] <= 10


def test_frozen_artifact_hashes():
    assert orchestration_holdout_v2_sha256(BENCHMARK) == EXPECTED_SHA256
    with gzip.open(BENCHMARK, "rb") as handle:
        assert hashlib.sha256(handle.read()).hexdigest() == EXPECTED_UNCOMPRESSED_SHA256


def test_novelty_universe_is_frozen_and_includes_known_oh1():
    result = validate_frozen_prior_benchmarks_v2()
    assert result["status"] == "PASS"
    assert result["benchmarks"] == 10
    assert result["questions"] == 430
    assert result["includes_oh1"] is True
    assert result["paths"] == [str(path) for path in FROZEN_PRIOR_BENCHMARK_PATHS]
    assert Path("data/benchmarks/orchestration_holdout_v1_0_0.csv.gz") in (
        FROZEN_PRIOR_BENCHMARK_PATHS
    )


def test_prospective_novelty_gate_passes_against_frozen_history():
    suite = load_orchestration_holdout_v2(BENCHMARK)
    result = validate_orchestration_holdout_v2_novelty(
        suite,
        FROZEN_PRIOR_BENCHMARK_PATHS,
        max_similarity_allowed=0.70,
    )
    assert result["status"] == "PASS"
    assert result["new_cases"] == 56
    assert result["prior_benchmarks_compared"] == 10
    assert result["prior_questions_compared"] == 430
    assert result["normalized_exact_overlap"] == 0
    assert result["highest_sequence_similarity"] <= 0.70


def test_novelty_gate_rejects_exact_normalized_overlap(tmp_path: Path):
    suite = load_orchestration_holdout_v2(BENCHMARK)
    prior = tmp_path / "prior.csv"
    prior.write_text(
        "id,question\nold,\"" + suite.cases[0].question.upper().replace('"', '""') + "\"\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="repetição exata normalizada"):
        validate_orchestration_holdout_v2_novelty(
            suite,
            (prior,),
            max_similarity_allowed=1.0,
        )


def test_normalized_questions_are_unique_inside_oh2():
    suite = load_orchestration_holdout_v2(BENCHMARK)
    normalized = [normalize_question_v2(case.question) for case in suite.cases]
    assert len(normalized) == len(set(normalized))


def test_all_frozen_prior_paths_have_question_column():
    for path in FROZEN_PRIOR_BENCHMARK_PATHS:
        assert questions_from_benchmark_v2(path)
