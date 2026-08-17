from __future__ import annotations

import base64
import gzip
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean
from typing import Any

ORCHESTRATION_HOLDOUT_DIAGNOSTIC_VERSION = "1.0.0"
RAW_MEASUREMENT_SHA256 = "d2213529f505e9d566ab64f1f27aa412e14a348abf997dfdb3d868edbab8c4c5"
GZIP_MEASUREMENT_SHA256 = "ee960b344f5c0cfe796300983bdebd0d1552cf7ee8dc7b7aa400b9573128a54b"
BASE64_MEASUREMENT_SHA256 = "c3e76cb64232de40c79b52467d26d3ecb3fbbc48a9798074b9a09ce401ece381"


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_frozen_measurement(parts: list[str | Path]) -> dict[str, Any]:
    paths = [Path(path) for path in parts]
    encoded = "".join(path.read_text(encoding="utf-8") for path in paths).encode("ascii")
    if _sha256(encoded) != BASE64_MEASUREMENT_SHA256:
        raise ValueError("base64 da primeira medição OH1 divergiu do hash congelado")

    compressed = base64.b64decode(encoded, validate=True)
    if _sha256(compressed) != GZIP_MEASUREMENT_SHA256:
        raise ValueError("gzip da primeira medição OH1 divergiu do hash congelado")

    raw = gzip.decompress(compressed)
    if _sha256(raw) != RAW_MEASUREMENT_SHA256:
        raise ValueError("JSON da primeira medição OH1 divergiu do hash congelado")
    return json.loads(raw)


def _canon(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _counter_rows(counter: Counter[Any], *, names: tuple[str, ...]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for key, count in sorted(counter.items(), key=lambda item: (-item[1], _canon(item[0]))):
        values = key if isinstance(key, tuple) else (key,)
        record = {name: value for name, value in zip(names, values, strict=True)}
        record["count"] = count
        records.append(record)
    return records


def _component_failure_signature(row: dict[str, Any]) -> str:
    failures: list[str] = []
    if not row["status_exact"]:
        failures.append("status")
    if not row["source_set_exact"]:
        failures.append("sources")
    if row["data_required"] and not row["data_tool_exact"]:
        failures.append("data_tool")
    if row["data_required"] and not row["data_arguments_exact"]:
        failures.append("data_arguments")
    if row["knowledge_required"] and not row["knowledge_filters_joint_exact"]:
        failures.append("knowledge_filters")
    if row["web_required"] and not row["web_parameters_exact"]:
        failures.append("web_parameters")
    if not row["schema_valid"]:
        failures.append("schema")
    return "+".join(failures) if failures else "pass"


def _mode_share(values: list[str]) -> float:
    return Counter(values).most_common(1)[0][1] / len(values)


def _component_stability(rows: list[dict[str, Any]]) -> dict[str, float]:
    by_case: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_case[row["id"]].append(row)

    components = {
        "full_signature": lambda row: row["predicted_signature"],
        "status": lambda row: row["predicted_status"],
        "sources": lambda row: _canon(row["predicted_sources"]),
        "data_tool": lambda row: _canon(row["predicted_data_tool"]),
        "data_parameters": lambda row: _canon(row["predicted_data_parameters"]),
        "knowledge_filters": lambda row: _canon(
            {
                "scopes": row["predicted_knowledge_scopes"],
                "temporal_statuses": row["predicted_knowledge_temporal_statuses"],
                "source_classes": row["predicted_knowledge_source_classes"],
            }
        ),
        "web_parameters": lambda row: _canon(row["predicted_web_parameters"]),
    }
    return {
        name: mean(
            _mode_share([str(accessor(row)) for row in case_rows])
            for case_rows in by_case.values()
        )
        for name, accessor in components.items()
    }


def _mismatch_by_key(
    rows: list[dict[str, Any]],
    *,
    expected_field: str,
    predicted_field: str,
) -> dict[str, Any]:
    key_total: Counter[str] = Counter()
    key_exact: Counter[str] = Counter()
    patterns: Counter[tuple[str, str, str]] = Counter()
    for row in rows:
        expected = row[expected_field]
        predicted = row[predicted_field]
        keys = sorted(set(expected) | set(predicted))
        for key in keys:
            key_total[key] += 1
            expected_value = expected.get(key, "__MISSING__")
            predicted_value = predicted.get(key, "__MISSING__")
            if expected_value == predicted_value:
                key_exact[key] += 1
            else:
                patterns[(key, _canon(expected_value), _canon(predicted_value))] += 1
    return {
        "key_exact_rates": {
            key: key_exact[key] / key_total[key] for key in sorted(key_total)
        },
        "mismatch_patterns": _counter_rows(
            patterns,
            names=("key", "expected_json", "predicted_json"),
        ),
    }


def diagnose_measurement(measurement: dict[str, Any]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = measurement["evaluation"]["rows"]
    by_case: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_case[row["id"]].append(row)

    failure_signatures = Counter(_component_failure_signature(row) for row in rows)
    source_confusion: Counter[tuple[str, str]] = Counter()
    missing_sources: Counter[str] = Counter()
    extra_sources: Counter[str] = Counter()
    for row in rows:
        source_confusion[
            (_canon(row["expected_sources"]), _canon(row["predicted_sources"]))
        ] += 1
        missing_sources.update(row["under_routed_sources"])
        extra_sources.update(row["over_routed_sources"])

    knowledge_rows = [row for row in rows if row["knowledge_required"]]
    knowledge_scope_mismatch: Counter[tuple[str, str]] = Counter()
    knowledge_temporal_mismatch: Counter[tuple[str, str]] = Counter()
    knowledge_class_mismatch: Counter[tuple[str, str]] = Counter()
    knowledge_component_exact = Counter()
    for row in knowledge_rows:
        scope_exact = set(row["expected_knowledge_scopes"]) == set(
            row["predicted_knowledge_scopes"]
        )
        temporal_exact = set(row["expected_knowledge_temporal_statuses"]) == set(
            row["predicted_knowledge_temporal_statuses"]
        )
        class_exact = set(row["expected_knowledge_source_classes"]) == set(
            row["predicted_knowledge_source_classes"]
        )
        knowledge_component_exact["scopes"] += scope_exact
        knowledge_component_exact["temporal_statuses"] += temporal_exact
        knowledge_component_exact["source_classes"] += class_exact
        if not scope_exact:
            knowledge_scope_mismatch[
                (
                    _canon(row["expected_knowledge_scopes"]),
                    _canon(row["predicted_knowledge_scopes"]),
                )
            ] += 1
        if not temporal_exact:
            knowledge_temporal_mismatch[
                (
                    _canon(row["expected_knowledge_temporal_statuses"]),
                    _canon(row["predicted_knowledge_temporal_statuses"]),
                )
            ] += 1
        if not class_exact:
            knowledge_class_mismatch[
                (
                    _canon(row["expected_knowledge_source_classes"]),
                    _canon(row["predicted_knowledge_source_classes"]),
                )
            ] += 1

    web_rows = [row for row in rows if row["web_required"]]
    data_rows = [row for row in rows if row["data_required"]]

    category_summary: dict[str, dict[str, Any]] = {}
    for category in sorted({row["category"] for row in rows}):
        category_rows = [row for row in rows if row["category"] == category]
        category_summary[category] = {
            "rows": len(category_rows),
            "source_set_exact": sum(row["source_set_exact"] for row in category_rows),
            "full_plan_exact": sum(row["full_plan_exact"] for row in category_rows),
            "schema_violations": sum(not row["schema_valid"] for row in category_rows),
            "under_routed_rows": sum(bool(row["under_routed_sources"]) for row in category_rows),
            "over_routed_rows": sum(bool(row["over_routed_sources"]) for row in category_rows),
        }

    unstable_cases: list[dict[str, Any]] = []
    for case_id, case_rows in sorted(by_case.items()):
        signatures = [row["predicted_signature"] for row in case_rows]
        modal_count = Counter(signatures).most_common(1)[0][1]
        if modal_count < len(case_rows):
            unstable_cases.append(
                {
                    "id": case_id,
                    "category": case_rows[0]["category"],
                    "modal_share": modal_count / len(case_rows),
                    "source_set_exact_repetitions": sum(
                        row["source_set_exact"] for row in case_rows
                    ),
                    "full_plan_exact_repetitions": sum(
                        row["full_plan_exact"] for row in case_rows
                    ),
                }
            )

    structural_rows = [row for row in rows if not row["schema_valid"]]
    provider_failure_rows = [
        row
        for row in rows
        if isinstance(row["warning"], str)
        and row["warning"].startswith("ORCHESTRATOR_PROVIDER_FAILED")
    ]
    plan_failure_rows = [
        row
        for row in rows
        if isinstance(row["warning"], str)
        and row["warning"].startswith("ORCHESTRATOR_PLAN_INVALID")
    ]

    return {
        "artifact": "orchestration_holdout_v1_post_hoc_diagnostic",
        "version": ORCHESTRATION_HOLDOUT_DIAGNOSTIC_VERSION,
        "status": "POST_HOC_DIAGNOSTIC_ONLY",
        "source": {
            "measurement_version": measurement["version"],
            "benchmark_version": measurement["benchmark"]["version"],
            "benchmark_sha256": measurement["benchmark"]["sha256"],
            "raw_measurement_sha256": RAW_MEASUREMENT_SHA256,
            "candidate": measurement["candidate"],
            "prospective_gate_passed": measurement["prospective_gate"]["passed"],
        },
        "repetition_level": {
            "rows": len(rows),
            "source_set_exact": sum(row["source_set_exact"] for row in rows),
            "full_plan_exact": sum(row["full_plan_exact"] for row in rows),
            "under_routed_rows": sum(bool(row["under_routed_sources"]) for row in rows),
            "over_routed_rows": sum(bool(row["over_routed_sources"]) for row in rows),
            "failure_signatures": dict(sorted(failure_signatures.items())),
            "missing_sources": dict(sorted(missing_sources.items())),
            "extra_sources": dict(sorted(extra_sources.items())),
        },
        "source_set_confusion": _counter_rows(
            source_confusion,
            names=("expected_sources_json", "predicted_sources_json"),
        ),
        "data_parameterization": {
            "required_rows": len(data_rows),
            "tool_exact": sum(bool(row["data_tool_exact"]) for row in data_rows),
            "arguments_exact": sum(bool(row["data_arguments_exact"]) for row in data_rows),
            **_mismatch_by_key(
                data_rows,
                expected_field="expected_data_parameters",
                predicted_field="predicted_data_parameters",
            ),
        },
        "knowledge_parameterization": {
            "required_rows": len(knowledge_rows),
            "joint_exact": sum(
                bool(row["knowledge_filters_joint_exact"]) for row in knowledge_rows
            ),
            "component_exact_rates": {
                key: knowledge_component_exact[key] / len(knowledge_rows)
                for key in ("scopes", "temporal_statuses", "source_classes")
            },
            "scope_mismatches": _counter_rows(
                knowledge_scope_mismatch,
                names=("expected_json", "predicted_json"),
            ),
            "temporal_mismatches": _counter_rows(
                knowledge_temporal_mismatch,
                names=("expected_json", "predicted_json"),
            ),
            "source_class_mismatches": _counter_rows(
                knowledge_class_mismatch,
                names=("expected_json", "predicted_json"),
            ),
        },
        "web_parameterization": {
            "required_rows": len(web_rows),
            "joint_exact": sum(bool(row["web_parameters_exact"]) for row in web_rows),
            **_mismatch_by_key(
                web_rows,
                expected_field="expected_web_parameters",
                predicted_field="predicted_web_parameters",
            ),
        },
        "stability": {
            "component_mean_modal_share": _component_stability(rows),
            "unstable_cases": len(unstable_cases),
            "unstable_case_details": unstable_cases,
        },
        "structural_and_provider_failures": {
            "schema_violations": len(structural_rows),
            "provider_failures": len(provider_failure_rows),
            "plan_failures": len(plan_failure_rows),
            "schema_case_repetitions": [
                {"id": row["id"], "repeat": row["repeat"], "warning": row["warning"]}
                for row in structural_rows
            ],
            "provider_failure_case_repetitions": [
                {"id": row["id"], "repeat": row["repeat"], "warning": row["warning"]}
                for row in provider_failure_rows
            ],
            "plan_failure_case_repetitions": [
                {"id": row["id"], "repeat": row["repeat"], "warning": row["warning"]}
                for row in plan_failure_rows
            ],
        },
        "category_summary": category_summary,
        "governance": {
            "oh1_is_known": True,
            "post_hoc_only": True,
            "no_llm_call": True,
            "no_worker_execution": True,
            "no_retriever_execution": True,
            "no_web_search": True,
            "no_sql": True,
            "no_prompt_or_policy_tuning": True,
            "no_new_generalization_claim": True,
            "production_activation": False,
            "next_independent_evidence_requires_new_prospective_holdout_after_change": True,
        },
    }


def diagnostic_json(measurement: dict[str, Any]) -> str:
    return json.dumps(
        diagnose_measurement(measurement),
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    ) + "\n"
