import hashlib
import json
from pathlib import Path

MANIFEST = Path("data/manifests/joint_retrieval_holdout_3_0_0.json")
BENCHMARK = Path("data/benchmarks/joint_retrieval_holdout_v3_0_0.csv")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_jh3_manifest_preserves_freeze_and_first_independent_measurement() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))

    assert manifest["version"] == "3.0.0"
    assert manifest["status"] == "MEASURED_INDEPENDENT"
    assert manifest["benchmark"]["sha256"] == _sha256(BENCHMARK)
    assert manifest["benchmark"]["sha256"] == (
        "d9598b3d1c04d2ddf776a931afba864dc972c4dea73dd0ef774b1e93185dd4a8"
    )
    assert manifest["benchmark"]["cases"] == 48
    assert manifest["benchmark"]["category_counts"] == {
        "normative": 12,
        "methodology": 12,
        "cross_source": 12,
        "control_external": 12,
    }

    novelty = manifest["novelty"]
    assert novelty["prior_questions_compared"] == 230
    assert novelty["normalized_exact_overlap"] == 0
    assert novelty["prospective_max_similarity"] == 0.8
    assert novelty["highest_sequence_similarity"] <= 0.8

    flow = manifest["frozen_flow"]
    assert flow["router_version"] == "1.3.0"
    assert flow["router_source_git_blob_sha"] == (
        "7c82b42f4409110371dcb86e15672a328a0d54bd"
    )
    assert flow["retrieval_planner_version"] == "1.2.0"
    assert flow["retrieval_planner_source_git_blob_sha"] == (
        "7ee30359cb4457b0bd1a12b43d14f73be410ddaa"
    )

    measurement = manifest["measurement"]
    assert measurement["performed"] is True
    first = measurement["first_valid_measurement"]
    assert first["run_id"] == 31971798204
    assert first["head_sha"] == "137a92c0e0fbe9a727985b1d0b5f6ac5722d1f1f"
    assert first["python_3_11"]["job_id"] == 95225278235
    assert first["python_3_12"]["job_id"] == 95225278284
    assert set(first["reproduction_exact_for"]) == {
        "summary",
        "by_category",
        "route_confusion_matrix",
        "mismatch_ids",
        "mean_set_metrics",
    }

    summary = measurement["result"]["summary"]
    assert summary == {
        "cases": 48,
        "route_exact": 31,
        "route_exact_rate": 31 / 48,
        "scope_exact": 35,
        "scope_exact_rate": 35 / 48,
        "temporal_exact": 35,
        "temporal_exact_rate": 35 / 48,
        "filter_joint_exact": 33,
        "filter_joint_exact_rate": 33 / 48,
        "joint_exact": 27,
        "joint_exact_rate": 27 / 48,
    }


def test_jh3_manifest_preserves_category_and_governance_result() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    by_category = manifest["measurement"]["result"]["by_category"]

    assert by_category["normative"]["joint_exact"] == 7
    assert by_category["methodology"]["joint_exact"] == 6
    assert by_category["cross_source"]["joint_exact"] == 3
    assert by_category["control_external"]["joint_exact"] == 11

    descriptive = manifest["measurement"]["result"]["descriptive_layer_decomposition"]
    assert descriptive == {
        "pass": 27,
        "route_only": 6,
        "filter_only": 4,
        "route_and_filter": 11,
        "causal_attribution": False,
    }

    interpretation = manifest["interpretation"]
    assert interpretation["new_independent_generalization_evidence_observed"] is True
    assert interpretation["comparison_with_jh2_independent_is_unpaired"] is True
    assert interpretation["production_readiness_supported"] is False
    assert interpretation["llm_integration_unblocked"] is False
    assert interpretation["next_step"] == (
        "post_hoc_counterfactual_attribution_before_any_tuning"
    )

    governance = manifest["governance"]
    assert governance["benchmark_changed_after_freeze"] is False
    assert governance["router_or_planner_tuned_during_measurement"] is False
    assert governance["future_tuning_on_jh3_requires_new_independent_holdout"] is True
    assert governance["retriever_called"] is False
    assert governance["llm_called"] is False
    assert governance["sql_executed"] is False
    assert governance["external_embeddings_called"] is False
    assert governance["llm_activation_allowed"] is False
