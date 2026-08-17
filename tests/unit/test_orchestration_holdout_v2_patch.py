from __future__ import annotations

import gzip
import hashlib
from pathlib import Path

from cpgf.benchmark.orchestration_holdout_v2 import (
    FROZEN_PRIOR_BENCHMARK_PATHS,
    validate_orchestration_holdout_v2_capabilities,
    validate_orchestration_holdout_v2_novelty,
)
from cpgf.benchmark.orchestration_holdout_v2_patch import (
    CORRECTED_CASE_IDS,
    ORCHESTRATION_HOLDOUT_V2_PATCH_VERSION,
    load_orchestration_holdout_v2_patch,
    validate_question_only_patch,
)

ORIGINAL = Path("data/benchmarks/orchestration_holdout_v2_0_0.csv.gz")
CORRECTED = Path("data/benchmarks/orchestration_holdout_v2_0_1.csv.gz")
EXPECTED_SHA256 = "427174c3d6217bd4ae2770779d38e83e1f9366d39f7ac4a3fc5d41afe64dbcb6"
EXPECTED_UNCOMPRESSED_SHA256 = (
    "574a46a330a1783494d7b7cbe39e9f7d62f29d33f84754fcbef9b934343af6e6"
)


def test_corrected_holdout_loads_with_patch_version_and_same_shape():
    suite = load_orchestration_holdout_v2_patch(CORRECTED)
    assert suite.version == ORCHESTRATION_HOLDOUT_V2_PATCH_VERSION == "2.0.1"
    assert len(suite.cases) == 56
    assert [case.id for case in suite.cases] == [
        f"OH2-{index:03d}" for index in range(1, 57)
    ]


def test_patch_changes_only_expected_question_fields_and_preserves_all_oracles():
    result = validate_question_only_patch(ORIGINAL, CORRECTED)
    assert result == {
        "status": "PASS",
        "original_version": "2.0.0",
        "corrected_version": "2.0.1",
        "cases": 56,
        "changed_case_ids": list(CORRECTED_CASE_IDS),
        "changed_field": "question",
        "oracles_changed": False,
    }
    assert list(CORRECTED_CASE_IDS) == [
        "OH2-017",
        "OH2-038",
        "OH2-052",
        "OH2-053",
        "OH2-054",
    ]


def test_corrected_questions_make_frozen_normalization_contract_explicit():
    suite = load_orchestration_holdout_v2_patch(CORRECTED)
    by_id = {case.id: case.question for case in suite.cases}
    assert "últimos 15 dias" in by_id["OH2-017"].lower()
    assert "base normativa" in by_id["OH2-038"].lower()
    assert "fontes do projeto" in by_id["OH2-052"].lower()
    assert "base normativa" in by_id["OH2-053"].lower()
    assert "orientação institucional" in by_id["OH2-054"].lower()


def test_corrected_artifact_hashes_are_frozen():
    assert hashlib.sha256(CORRECTED.read_bytes()).hexdigest() == EXPECTED_SHA256
    with gzip.open(CORRECTED, "rb") as handle:
        assert hashlib.sha256(handle.read()).hexdigest() == EXPECTED_UNCOMPRESSED_SHA256


def test_corrected_holdout_preserves_capability_balance():
    suite = load_orchestration_holdout_v2_patch(CORRECTED)
    result = validate_orchestration_holdout_v2_capabilities(suite)
    assert result["cases"] == 56
    assert result["source_presence_counts"] == {
        "data": 32,
        "knowledge": 32,
        "web": 32,
    }
    assert result["data_tool_counts"] == {
        "overview": 6,
        "territorial_metric": 7,
        "territorial_ug_context": 4,
        "top_suppliers": 6,
        "top_ugs": 5,
        "trail_prevalence": 4,
    }


def test_corrected_holdout_retains_prospective_novelty_gate():
    suite = load_orchestration_holdout_v2_patch(CORRECTED)
    result = validate_orchestration_holdout_v2_novelty(
        suite,
        FROZEN_PRIOR_BENCHMARK_PATHS,
        max_similarity_allowed=0.70,
    )
    assert result["status"] == "PASS"
    assert result["prior_benchmarks_compared"] == 10
    assert result["prior_questions_compared"] == 430
    assert result["normalized_exact_overlap"] == 0
    assert result["highest_sequence_similarity"] <= 0.70
