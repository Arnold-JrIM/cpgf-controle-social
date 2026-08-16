import json
from pathlib import Path

from cpgf.benchmark import benchmark_sha256
from cpgf.version import RETRIEVAL_PLANNER_VERSION, ROUTER_VERSION

MANIFEST = Path("data/manifests/retrieval_planner_1_1_0.json")
DEVELOPMENT = Path("data/benchmarks/knowledge_retrieval_v1_0_0.csv")
KNOWN_HOLDOUT = Path("data/benchmarks/retrieval_planner_holdout_v1_0_0.csv")


def test_retrieval_planner_1_1_manifest_preserves_known_regression_contract() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))

    assert manifest["version"] == RETRIEVAL_PLANNER_VERSION == "1.1.0"
    assert manifest["router_version"] == ROUTER_VERSION == "1.2.0"
    assert manifest["status"] == "KNOWN_REGRESSION_FROZEN"

    development = manifest["known_regression_sets"]["development"]
    holdout = manifest["known_regression_sets"]["retrieval_planner_holdout_v1"]
    assert development["sha256"] == benchmark_sha256(DEVELOPMENT)
    assert holdout["sha256"] == benchmark_sha256(KNOWN_HOLDOUT)

    for item in (development, holdout):
        assert item["cases"] == 30
        assert item["scope_exact"] == 30
        assert item["temporal_exact"] == 30
        assert item["joint_exact"] == 30
        assert item["scope_exact_rate"] == 1.0
        assert item["temporal_exact_rate"] == 1.0
        assert item["joint_exact_rate"] == 1.0
        assert item["divergent_ids"] == []

    assert holdout["first_independent_measurement_before_tuning"]["joint_exact"] == 14
    assert holdout["after_router_1_2_before_planner_tuning"]["joint_exact"] == 21
    assert len(holdout["after_router_1_2_before_planner_tuning"]["planner_failure_ids"]) == 9

    governance = manifest["governance"]
    assert governance["new_generalization_claim"] is False
    assert governance["known_60_of_60_is_production_accuracy_claim"] is False
    assert governance["router_modified_in_increment"] is False
    assert governance["case_id_specific_rules_added"] is False
    assert governance["llm_called"] is False
    assert governance["sql_executed"] is False
    assert governance["llm_activation_allowed_before_next_holdout"] is False
