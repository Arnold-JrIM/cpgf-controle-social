from __future__ import annotations

import gzip
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

DIAGNOSTIC_VERSION = "1.0.0"
RAW_MEASUREMENT_SHA256 = "b935b69b545c1e7536ac3da84e857ad9bc968932f586202b954433c369a8bcc2"


def load_measurement(path: str | Path) -> dict[str, Any]:
    path = Path(path)
    if path.suffix == ".gz":
        with gzip.open(path, "rt", encoding="utf-8") as handle:
            return json.load(handle)
    return json.loads(path.read_text(encoding="utf-8"))


def _mode_prediction(
    rows: list[dict[str, Any]],
) -> tuple[tuple[str, tuple[str, ...], tuple[str, ...]], int]:
    counts = Counter(
        (
            row["predicted_route"],
            tuple(row["predicted_scopes"]),
            tuple(row["predicted_temporal_statuses"]),
        )
        for row in rows
    )
    prediction, count = sorted(counts.items(), key=lambda item: (-item[1], item[0]))[0]
    return prediction, count


def diagnose_measurement(measurement: dict[str, Any]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = measurement["evaluation"]["candidate_B"]["rows"]
    by_case: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_case[row["id"]].append(row)

    exactness_patterns: Counter[str] = Counter()
    route_confusion: Counter[tuple[str, str]] = Counter()
    scope_mismatches: Counter[tuple[tuple[str, ...], tuple[str, ...]]] = Counter()
    temporal_mismatches: Counter[tuple[tuple[str, ...], tuple[str, ...]]] = Counter()

    for row in rows:
        exactness_patterns[
            ("R" if row["route_exact"] else "r")
            + ("S" if row["scope_exact"] else "s")
            + ("T" if row["temporal_exact"] else "t")
        ] += 1
        route_confusion[(row["expected_route"], row["predicted_route"])] += 1
        if not row["scope_exact"]:
            scope_mismatches[
                (tuple(row["expected_scopes"]), tuple(row["predicted_scopes"]))
            ] += 1
        if not row["temporal_exact"]:
            temporal_mismatches[
                (
                    tuple(row["expected_temporal_statuses"]),
                    tuple(row["predicted_temporal_statuses"]),
                )
            ] += 1

    modal_cases: list[dict[str, Any]] = []
    class_case_ids: dict[str, list[str]] = defaultdict(list)
    for case_id, case_rows in sorted(by_case.items()):
        modal_prediction, modal_count = _mode_prediction(case_rows)
        expected = case_rows[0]
        route_exact = modal_prediction[0] == expected["expected_route"]
        scope_exact = list(modal_prediction[1]) == expected["expected_scopes"]
        temporal_exact = list(modal_prediction[2]) == expected["expected_temporal_statuses"]
        filter_exact = scope_exact and temporal_exact
        joint_exact = route_exact and filter_exact

        if joint_exact:
            classification = "pass"
        elif not route_exact and filter_exact:
            classification = "route_only"
        elif route_exact and not filter_exact:
            classification = "filters_only"
        else:
            classification = "route_and_filters"

        class_case_ids[classification].append(case_id)
        modal_cases.append(
            {
                "id": case_id,
                "category": expected["category"],
                "classification": classification,
                "modal_count": modal_count,
                "expected_route": expected["expected_route"],
                "modal_route": modal_prediction[0],
                "expected_scopes": expected["expected_scopes"],
                "modal_scopes": list(modal_prediction[1]),
                "expected_temporal_statuses": expected["expected_temporal_statuses"],
                "modal_temporal_statuses": list(modal_prediction[2]),
            }
        )

    category_summary: dict[str, dict[str, Any]] = {}
    for category in sorted({case["category"] for case in modal_cases}):
        cases = [case for case in modal_cases if case["category"] == category]
        category_summary[category] = {
            "cases": len(cases),
            "modal_route_exact": sum(
                case["classification"] in {"pass", "filters_only"} for case in cases
            ),
            "modal_filter_exact": sum(
                case["classification"] in {"pass", "route_only"} for case in cases
            ),
            "modal_joint_pass": sum(case["classification"] == "pass" for case in cases),
            "class_counts": dict(
                sorted(Counter(case["classification"] for case in cases).items())
            ),
        }

    route_errors = sum(not row["route_exact"] for row in rows)
    over_route_to_composite = sum(
        row["predicted_route"] == "composite" and not row["route_exact"] for row in rows
    )
    composite_rows = [row for row in rows if row["expected_route"] == "composite"]
    composite_route_recall = (
        sum(row["route_exact"] for row in composite_rows) / len(composite_rows)
        if composite_rows
        else 0.0
    )

    return {
        "artifact": "semantic_candidate_jh5_post_hoc_diagnostic",
        "version": DIAGNOSTIC_VERSION,
        "status": "POST_HOC_DIAGNOSTIC_ONLY",
        "source": {
            "benchmark_version": measurement["benchmark"]["version"],
            "benchmark_sha256": measurement["benchmark"]["sha256"],
            "raw_measurement_sha256": RAW_MEASUREMENT_SHA256,
            "candidate": "B_llm_route",
            "measurement_result_status": "MEASURED_INDEPENDENT_GATE_FAIL",
        },
        "observed_repetition_level": {
            "rows": len(rows),
            "joint_passes": sum(row["joint_exact"] for row in rows),
            "joint_failures": sum(not row["joint_exact"] for row in rows),
            "route_failures": route_errors,
            "filter_failures": sum(not row["filter_joint_exact"] for row in rows),
            "scope_failures": sum(not row["scope_exact"] for row in rows),
            "temporal_failures": sum(not row["temporal_exact"] for row in rows),
            "exactness_patterns": dict(sorted(exactness_patterns.items())),
        },
        "route_confusion": [
            {"expected": expected, "predicted": predicted, "count": count}
            for (expected, predicted), count in sorted(route_confusion.items())
        ],
        "modal_case_level": {
            "cases": len(modal_cases),
            "joint_passes": len(class_case_ids["pass"]),
            "route_exact": sum(
                case["classification"] in {"pass", "filters_only"}
                for case in modal_cases
            ),
            "filter_exact": sum(
                case["classification"] in {"pass", "route_only"}
                for case in modal_cases
            ),
            "class_counts": {
                key: len(class_case_ids[key])
                for key in ("pass", "route_only", "filters_only", "route_and_filters")
            },
            "class_case_ids": {
                key: class_case_ids[key]
                for key in ("route_only", "filters_only", "route_and_filters")
            },
            "unstable_case_ids": ["JH5-003", "JH5-012", "JH5-023"],
        },
        "category_modal_summary": category_summary,
        "scope_mismatch_patterns": [
            {"expected": list(expected), "predicted": list(predicted), "count": count}
            for (expected, predicted), count in sorted(
                scope_mismatches.items(), key=lambda item: (-item[1], item[0])
            )
        ],
        "temporal_mismatch_patterns": [
            {"expected": list(expected), "predicted": list(predicted), "count": count}
            for (expected, predicted), count in sorted(
                temporal_mismatches.items(), key=lambda item: (-item[1], item[0])
            )
        ],
        "architectural_reading": {
            "route_layer_result": "semantic routing is strong but not sufficient",
            "composite_route_recall_across_repetitions": composite_route_recall,
            "route_errors_direction": (
                f"all {route_errors} route errors are over-routing from knowledge/methodology "
                "to composite"
                if route_errors == over_route_to_composite
                else "route errors are mixed"
            ),
            "cross_source_issue": (
                "all 36 cross_source route decisions are exact, but 24/36 joint rows fail "
                "because filters do not encode the required evidence combination"
            ),
            "control_external_issue": (
                "all 36 control_external route decisions are exact, but 12/36 joint rows fail "
                "on filters"
            ),
            "design_implication": (
                "replace exclusive documentary route as the primary semantic contract with "
                "multi-label evidence needs; keep deterministic execution boundaries"
            ),
        },
        "governance": {
            "jh5_is_known": True,
            "no_retuning_on_jh5_for_independence_claim": True,
            "no_new_generalization_claim": True,
            "no_retriever_execution": True,
            "no_llm_call": True,
            "no_production_activation": True,
            "next_independent_evidence_requires_new_prospective_holdout": True,
        },
    }


def diagnostic_json(measurement: dict[str, Any]) -> str:
    return (
        json.dumps(diagnose_measurement(measurement), ensure_ascii=False, indent=2, sort_keys=True)
        + "\n"
    )
