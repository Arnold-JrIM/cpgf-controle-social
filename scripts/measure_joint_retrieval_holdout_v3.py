from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

from cpgf.ai import plan_knowledge_retrieval, route_question
from cpgf.benchmark.joint_retrieval_v3 import (
    joint_holdout_v3_sha256,
    load_joint_retrieval_holdout_v3,
)

BENCHMARK = Path("data/benchmarks/joint_retrieval_holdout_v3_0_0.csv")
MANIFEST = Path("data/manifests/joint_retrieval_holdout_3_0_0.json")


def _set_metrics(expected: set[str], predicted: set[str]) -> tuple[float, float]:
    if not predicted:
        precision = 1.0 if not expected else 0.0
    else:
        precision = len(expected & predicted) / len(predicted)
    recall = len(expected & predicted) / len(expected) if expected else 1.0
    return precision, recall


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Primeira medição independente do Joint Holdout 3.0. "
            "A nota obtida nunca determina sucesso/falha do processo."
        )
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if manifest["status"] != "FROZEN_BEFORE_MEASUREMENT":
        raise ValueError(
            "Medição oficial só é permitida no estado FROZEN_BEFORE_MEASUREMENT; "
            f"estado atual: {manifest['status']}"
        )
    if joint_holdout_v3_sha256(BENCHMARK) != manifest["benchmark"]["sha256"]:
        raise ValueError("Benchmark divergiu do SHA congelado antes da medição")

    suite = load_joint_retrieval_holdout_v3(BENCHMARK)
    rows: list[dict[str, object]] = []
    by_category: defaultdict[str, Counter[str]] = defaultdict(Counter)
    confusion: defaultdict[str, Counter[str]] = defaultdict(Counter)
    mismatch_ids: dict[str, list[str]] = {
        "route": [],
        "scope": [],
        "temporal": [],
        "filter_joint": [],
        "joint": [],
    }
    scope_precision: list[float] = []
    scope_recall: list[float] = []
    temporal_precision: list[float] = []
    temporal_recall: list[float] = []

    # O oráculo não participa da previsão: primeiro Router -> Planner, depois comparação.
    for case in suite.cases:
        decision = route_question(case.question)
        plan = plan_knowledge_retrieval(case.question, decision=decision)

        expected_scopes = {item.value for item in case.expected_scopes}
        predicted_scopes = {item.value for item in plan.scopes}
        expected_temporal = {item.value for item in case.expected_temporal_statuses}
        predicted_temporal = {item.value for item in plan.temporal_statuses}

        route_exact = decision.route == case.expected_route
        scope_exact = expected_scopes == predicted_scopes
        temporal_exact = expected_temporal == predicted_temporal
        filter_joint_exact = scope_exact and temporal_exact
        joint_exact = route_exact and filter_joint_exact

        sp, sr = _set_metrics(expected_scopes, predicted_scopes)
        tp, tr = _set_metrics(expected_temporal, predicted_temporal)
        scope_precision.append(sp)
        scope_recall.append(sr)
        temporal_precision.append(tp)
        temporal_recall.append(tr)

        category = case.category.value
        for key, value in (
            ("route_exact", route_exact),
            ("scope_exact", scope_exact),
            ("temporal_exact", temporal_exact),
            ("filter_joint_exact", filter_joint_exact),
            ("joint_exact", joint_exact),
        ):
            by_category[category][key] += int(value)
        by_category[category]["cases"] += 1
        confusion[case.expected_route.value][decision.route.value] += 1

        for key, exact in (
            ("route", route_exact),
            ("scope", scope_exact),
            ("temporal", temporal_exact),
            ("filter_joint", filter_joint_exact),
            ("joint", joint_exact),
        ):
            if not exact:
                mismatch_ids[key].append(case.id)

        rows.append(
            {
                "id": case.id,
                "category": category,
                "question": case.question,
                "expected_route": case.expected_route.value,
                "predicted_route": decision.route.value,
                "route_exact": route_exact,
                "expected_scopes": sorted(expected_scopes),
                "predicted_scopes": sorted(predicted_scopes),
                "scope_exact": scope_exact,
                "expected_temporal_statuses": sorted(expected_temporal),
                "predicted_temporal_statuses": sorted(predicted_temporal),
                "temporal_exact": temporal_exact,
                "filter_joint_exact": filter_joint_exact,
                "joint_exact": joint_exact,
            }
        )

    cases = len(rows)
    summary = {
        "cases": cases,
        "route_exact": sum(bool(row["route_exact"]) for row in rows),
        "scope_exact": sum(bool(row["scope_exact"]) for row in rows),
        "temporal_exact": sum(bool(row["temporal_exact"]) for row in rows),
        "filter_joint_exact": sum(bool(row["filter_joint_exact"]) for row in rows),
        "joint_exact": sum(bool(row["joint_exact"]) for row in rows),
    }
    for key in ("route_exact", "scope_exact", "temporal_exact", "filter_joint_exact", "joint_exact"):
        summary[f"{key}_rate"] = summary[key] / cases if cases else 0.0

    category_payload: dict[str, dict[str, float | int]] = {}
    for category, counts in sorted(by_category.items()):
        n = counts["cases"]
        item: dict[str, float | int] = {"cases": n}
        for key in (
            "route_exact",
            "scope_exact",
            "temporal_exact",
            "filter_joint_exact",
            "joint_exact",
        ):
            item[key] = counts[key]
            item[f"{key}_rate"] = counts[key] / n if n else 0.0
        category_payload[category] = item

    payload = {
        "artifact": "joint_retrieval_holdout_v3_measurement",
        "version": "3.0.0",
        "status": "INDEPENDENT_MEASUREMENT",
        "benchmark_sha256": manifest["benchmark"]["sha256"],
        "frozen_flow": manifest["frozen_flow"],
        "summary": summary,
        "by_category": category_payload,
        "route_confusion_matrix": {
            expected: dict(sorted(predicted.items()))
            for expected, predicted in sorted(confusion.items())
        },
        "mismatch_ids": mismatch_ids,
        "mean_set_metrics": {
            "scope_precision": sum(scope_precision) / cases,
            "scope_recall": sum(scope_recall) / cases,
            "temporal_precision": sum(temporal_precision) / cases,
            "temporal_recall": sum(temporal_recall) / cases,
        },
        "cases_detail": rows,
        "governance": {
            "predictions_generated_before_oracle_comparison": True,
            "performance_threshold_applied": False,
            "low_performance_causes_workflow_failure": False,
            "benchmark_modified_after_freeze": False,
            "router_or_planner_tuned_during_measurement": False,
            "retriever_called": False,
            "llm_called": False,
            "sql_executed": False,
            "external_embeddings_called": False,
            "holdout_becomes_known_after_this_measurement": True,
        },
    }
    args.output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
