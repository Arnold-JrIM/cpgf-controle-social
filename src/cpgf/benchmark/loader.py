from __future__ import annotations

import csv
from pathlib import Path

from cpgf.knowledge import load_source_catalog

from .models import BenchmarkCase, BenchmarkSuite

_LIST_FIELDS_SEMICOLON = {
    "expected_tools",
    "gold_document_ids",
    "supporting_document_ids",
    "expected_scopes",
    "expected_temporal_statuses",
    "expected_trails",
}
_LIST_FIELDS_PIPE = {"expected_concepts", "forbidden_claims"}
_BOOL_FIELDS = {"requires_serving", "requires_knowledge", "freshness_sensitive"}


def _split(value: str, separator: str) -> tuple[str, ...]:
    return tuple(item.strip() for item in value.split(separator) if item.strip())


def load_benchmark(path: Path | str) -> BenchmarkSuite:
    path = Path(path)
    cases: list[BenchmarkCase] = []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            payload: dict[str, object] = dict(row)
            for field in _LIST_FIELDS_SEMICOLON:
                payload[field] = _split(str(payload.get(field, "")), ";")
            for field in _LIST_FIELDS_PIPE:
                payload[field] = _split(str(payload.get(field, "")), "|")
            for field in _BOOL_FIELDS:
                payload[field] = str(payload.get(field, "")).strip() == "1"
            notes = str(payload.get("notes", "")).strip()
            payload["notes"] = notes or None
            cases.append(BenchmarkCase.model_validate(payload))
    return BenchmarkSuite(cases=tuple(cases))


def validate_benchmark_against_catalog(
    suite: BenchmarkSuite,
    catalog_path: Path | str,
) -> dict[str, object]:
    catalog = load_source_catalog(Path(catalog_path))
    catalog_ids = {item.document_id for item in catalog}
    referenced = {
        document_id
        for case in suite.cases
        for document_id in (*case.gold_document_ids, *case.supporting_document_ids)
    }
    missing = sorted(referenced - catalog_ids)
    if missing:
        raise ValueError(f"Documentos-gabarito ausentes do Knowledge: {missing}")

    return {
        "status": "PASS",
        "benchmark_version": suite.benchmark_version,
        "cases": len(suite.cases),
        "knowledge_cases": sum(case.requires_knowledge for case in suite.cases),
        "serving_cases": sum(case.requires_serving for case in suite.cases),
        "freshness_sensitive_cases": sum(case.freshness_sensitive for case in suite.cases),
        "gold_documents": len(referenced),
    }
