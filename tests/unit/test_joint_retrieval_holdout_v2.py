import json
from collections import Counter
from pathlib import Path

from cpgf.benchmark import (
    joint_holdout_sha256,
    load_joint_retrieval_holdout,
    validate_joint_holdout_against_catalog,
    validate_joint_holdout_novelty,
)

HOLDOUT = Path("data/benchmarks/joint_retrieval_holdout_v2_0_0.csv")
MANIFEST = Path("data/manifests/joint_retrieval_holdout_2_0_0.json")
CATALOG = Path("data/knowledge/source_catalog.json")
PRIOR = (
    Path("data/benchmarks/knowledge_retrieval_v1_0_0.csv"),
    Path("data/benchmarks/retrieval_planner_holdout_v1_0_0.csv"),
    Path("data/benchmarks/assistant_v1_0_0.csv"),
    Path("data/benchmarks/assistant_router_holdout_v1_0_0.csv"),
    Path("data/benchmarks/assistant_router_holdout_v2_0_0.csv"),
)


def test_joint_holdout_v2_matches_frozen_contract() -> None:
    suite = load_joint_retrieval_holdout(HOLDOUT)
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))

    assert suite.version == "2.0.0"
    assert len(suite.cases) == 40
    assert joint_holdout_sha256(HOLDOUT) == manifest["benchmark"]["sha256"]
    assert manifest["benchmark"]["sha256"] == (
        "47d29dfaa0e71ea4b9c7c813b02d1001fa32a7605a241f95708686718a5b7ec7"
    )
    assert manifest["status"] == "FROZEN_BEFORE_MEASUREMENT"
    assert manifest["measurement"]["first_valid_measurement_run_id"] is None


def test_joint_holdout_v2_has_planned_balance() -> None:
    suite = load_joint_retrieval_holdout(HOLDOUT)

    assert Counter(case.category.value for case in suite.cases) == {
        "normative": 10,
        "methodology": 10,
        "cross_source": 14,
        "control_external": 6,
    }
    assert Counter(case.expected_route.value for case in suite.cases) == {
        "knowledge": 17,
        "methodology": 10,
        "composite": 13,
    }
    assert sum(case.freshness_sensitive for case in suite.cases) == 2


def test_joint_holdout_v2_references_governed_catalog() -> None:
    suite = load_joint_retrieval_holdout(HOLDOUT)
    result = validate_joint_holdout_against_catalog(suite, CATALOG)

    assert result["status"] == "PASS"
    assert result["cases"] == 40
    assert result["gold_documents"] == 28
    assert result["referenced_documents"] == 29


def test_joint_holdout_v2_has_no_normalized_exact_overlap_with_prior_sets() -> None:
    suite = load_joint_retrieval_holdout(HOLDOUT)
    result = validate_joint_holdout_novelty(suite, PRIOR)

    assert result["status"] == "PASS"
    assert result["new_cases"] == 40
    assert result["normalized_exact_overlap"] == 0


def test_joint_holdout_v2_manifest_freezes_router_and_planner_before_measurement() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    frozen = manifest["frozen_flow"]
    governance = manifest["governance"]

    assert frozen["router_version"] == "1.2.0"
    assert frozen["retrieval_planner_version"] == "1.1.0"
    assert frozen["knowledge_version"] == "1.2.0"
    assert manifest["oracle"]["expected_route_frozen"] is True
    assert manifest["oracle"]["expected_scopes_frozen"] is True
    assert manifest["oracle"]["expected_temporal_statuses_frozen"] is True
    assert governance["benchmark_measured_before_freeze"] is False
    assert governance["llm_called"] is False
    assert governance["sql_executed"] is False
