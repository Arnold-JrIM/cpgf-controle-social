from __future__ import annotations

import csv
import hashlib
import re
from collections import Counter, defaultdict
from enum import StrEnum
from pathlib import Path
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field, model_validator

from cpgf.knowledge import load_source_catalog
from cpgf.knowledge.models import CorpusScope, TemporalStatus
from cpgf.version import RETRIEVAL_BENCHMARK_VERSION

_CASE_ID = re.compile(r"^KRET-\d{3}$")
_TRAILS = {f"T{i:02d}" for i in range(1, 10)}
_LIST_FIELDS = {
    "gold_document_ids",
    "supporting_document_ids",
    "expected_scopes",
    "expected_temporal_statuses",
    "expected_trails",
}


class RetrievalCategory(StrEnum):
    NORMATIVE = "normative"
    METHODOLOGY = "methodology"
    CONTROL_EXTERNAL = "control_external"
    CROSS_SOURCE = "cross_source"


class RetrievalBenchmarkCase(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    category: RetrievalCategory
    question: str = Field(min_length=10, max_length=500)
    gold_document_ids: tuple[str, ...]
    supporting_document_ids: tuple[str, ...] = ()
    expected_scopes: tuple[CorpusScope, ...]
    expected_temporal_statuses: tuple[TemporalStatus, ...] = ()
    expected_trails: tuple[str, ...] = ()
    freshness_sensitive: bool = False
    notes: str | None = None

    @model_validator(mode="after")
    def validate_contract(self) -> "RetrievalBenchmarkCase":
        if not _CASE_ID.fullmatch(self.id):
            raise ValueError(f"ID inválido: {self.id}")
        if not self.gold_document_ids:
            raise ValueError("Cada caso requer ao menos um documento-gabarito")
        if len(self.gold_document_ids) != len(set(self.gold_document_ids)):
            raise ValueError(f"Documentos-gabarito duplicados em {self.id}")
        if not self.expected_scopes:
            raise ValueError("Cada caso requer ao menos um escopo esperado")
        invalid_trails = sorted(set(self.expected_trails) - _TRAILS)
        if invalid_trails:
            raise ValueError(f"Trilhas inválidas: {invalid_trails}")
        return self


class RetrievalBenchmarkSuite(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    benchmark_version: str = RETRIEVAL_BENCHMARK_VERSION
    title: str = "Benchmark documental de recuperação do Knowledge CPGF"
    cases: tuple[RetrievalBenchmarkCase, ...]

    @model_validator(mode="after")
    def validate_suite(self) -> "RetrievalBenchmarkSuite":
        if self.benchmark_version != RETRIEVAL_BENCHMARK_VERSION:
            raise ValueError(
                f"Versão do benchmark de recuperação deve ser {RETRIEVAL_BENCHMARK_VERSION}"
            )
        if not 20 <= len(self.cases) <= 60:
            raise ValueError("Benchmark de recuperação deve conter entre 20 e 60 casos")
        ids = [case.id for case in self.cases]
        if len(ids) != len(set(ids)):
            raise ValueError("IDs duplicados no benchmark de recuperação")
        categories = {case.category for case in self.cases}
        if categories != set(RetrievalCategory):
            raise ValueError("Benchmark de recuperação deve cobrir todas as categorias")
        return self


class Retriever(Protocol):
    def search(self, query: str, *, limit: int = 5, **filters: object) -> list[object]: ...


def _split(value: str) -> tuple[str, ...]:
    return tuple(item.strip() for item in value.split(";") if item.strip())


def load_retrieval_benchmark(path: Path | str) -> RetrievalBenchmarkSuite:
    path = Path(path)
    cases: list[RetrievalBenchmarkCase] = []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            payload: dict[str, object] = dict(row)
            for field in _LIST_FIELDS:
                payload[field] = _split(str(payload.get(field, "")))
            payload["freshness_sensitive"] = (
                str(payload.get("freshness_sensitive", "")).strip() == "1"
            )
            notes = str(payload.get("notes", "")).strip()
            payload["notes"] = notes or None
            cases.append(RetrievalBenchmarkCase.model_validate(payload))
    return RetrievalBenchmarkSuite(cases=tuple(cases))


def benchmark_sha256(path: Path | str) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def validate_retrieval_benchmark_against_catalog(
    suite: RetrievalBenchmarkSuite,
    catalog_path: Path | str,
) -> dict[str, object]:
    catalog = load_source_catalog(Path(catalog_path))
    by_id = {item.document_id: item for item in catalog}
    referenced = {
        document_id
        for case in suite.cases
        for document_id in (*case.gold_document_ids, *case.supporting_document_ids)
    }
    missing = sorted(referenced - set(by_id))
    if missing:
        raise ValueError(f"Documentos do benchmark ausentes do Knowledge: {missing}")

    non_default_gold = sorted(
        {
            document_id
            for case in suite.cases
            for document_id in case.gold_document_ids
            if not bool(by_id[document_id].retrieval_default)
        }
    )
    if non_default_gold:
        raise ValueError(
            "Documento-gabarito fora da recuperação padrão: " + ", ".join(non_default_gold)
        )

    return {
        "status": "PASS",
        "retrieval_benchmark_version": suite.benchmark_version,
        "cases": len(suite.cases),
        "gold_documents": len(
            {document_id for case in suite.cases for document_id in case.gold_document_ids}
        ),
        "referenced_documents": len(referenced),
        "freshness_sensitive_cases": sum(case.freshness_sensitive for case in suite.cases),
        "category_counts": dict(Counter(case.category.value for case in suite.cases)),
    }


def _document_ranking(hits: list[object], *, k: int) -> list[str]:
    ranking: list[str] = []
    seen: set[str] = set()
    for hit in hits:
        document_id = str(hit.document_id)
        if document_id in seen:
            continue
        seen.add(document_id)
        ranking.append(document_id)
        if len(ranking) == k:
            break
    return ranking


def _average_precision_at_k(ranking: list[str], gold: set[str], k: int) -> float:
    hits = 0
    precision_sum = 0.0
    for rank, document_id in enumerate(ranking[:k], start=1):
        if document_id in gold:
            hits += 1
            precision_sum += hits / rank
    denominator = min(len(gold), k)
    return 0.0 if denominator == 0 else precision_sum / denominator


def evaluate_retrieval_benchmark(
    suite: RetrievalBenchmarkSuite,
    retriever: Retriever,
    *,
    k: int = 5,
    governed: bool = True,
) -> dict[str, object]:
    if not 1 <= k <= 20:
        raise ValueError("k deve estar entre 1 e 20")

    rows: list[dict[str, object]] = []
    reciprocal_ranks: list[float] = []
    recall_values: list[float] = []
    average_precisions: list[float] = []
    per_category_rows: dict[str, list[dict[str, object]]] = defaultdict(list)

    candidate_limit = min(20, max(k * 4, k))
    for case in suite.cases:
        filters: dict[str, object] = {}
        if governed:
            filters["scopes"] = {scope.value for scope in case.expected_scopes}
            if case.expected_temporal_statuses:
                filters["temporal_statuses"] = {
                    status.value for status in case.expected_temporal_statuses
                }

        hits = retriever.search(case.question, limit=candidate_limit, **filters)
        ranking = _document_ranking(hits, k=k)
        gold = set(case.gold_document_ids)
        relevant_positions = [
            rank for rank, document_id in enumerate(ranking, start=1) if document_id in gold
        ]
        first_rank = min(relevant_positions) if relevant_positions else None
        recall = len(gold.intersection(ranking)) / len(gold)
        reciprocal_rank = 0.0 if first_rank is None else 1.0 / first_rank
        average_precision = _average_precision_at_k(ranking, gold, k)
        row = {
            "id": case.id,
            "category": case.category.value,
            "gold_document_ids": sorted(gold),
            "retrieved_document_ids": ranking,
            "first_relevant_rank": first_rank,
            f"hit_at_{k}": first_rank is not None,
            f"document_recall_at_{k}": recall,
            "reciprocal_rank": reciprocal_rank,
            f"average_precision_at_{k}": average_precision,
        }
        rows.append(row)
        per_category_rows[case.category.value].append(row)
        reciprocal_ranks.append(reciprocal_rank)
        recall_values.append(recall)
        average_precisions.append(average_precision)

    def summarize(items: list[dict[str, object]]) -> dict[str, object]:
        count = len(items)
        if count == 0:
            return {"cases": 0}
        return {
            "cases": count,
            f"hit_rate_at_{k}": sum(bool(item[f"hit_at_{k}"]) for item in items) / count,
            f"mean_document_recall_at_{k}": sum(
                float(item[f"document_recall_at_{k}"]) for item in items
            )
            / count,
            "mrr": sum(float(item["reciprocal_rank"]) for item in items) / count,
            f"map_at_{k}": sum(float(item[f"average_precision_at_{k}"]) for item in items)
            / count,
        }

    return {
        "benchmark_version": suite.benchmark_version,
        "governed": governed,
        "k": k,
        "summary": summarize(rows),
        "by_category": {
            category: summarize(items) for category, items in sorted(per_category_rows.items())
        },
        "cases": rows,
    }
