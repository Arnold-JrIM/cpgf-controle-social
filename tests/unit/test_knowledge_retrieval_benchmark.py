from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from cpgf.benchmark import (
    RetrievalCategory,
    evaluate_retrieval_benchmark,
    load_retrieval_benchmark,
    validate_retrieval_benchmark_against_catalog,
)

BENCHMARK = Path("data/benchmarks/knowledge_retrieval_v1_0_0.csv")
CATALOG = Path("data/knowledge/source_catalog.json")


@dataclass(frozen=True)
class _Hit:
    document_id: str


class _PerfectDocumentRetriever:
    def __init__(self, gold_by_question: dict[str, tuple[str, ...]]):
        self._gold_by_question = gold_by_question

    def search(self, query: str, *, limit: int = 5, **filters: object) -> list[_Hit]:
        del filters
        gold = self._gold_by_question[query]
        # Repete o primeiro documento para exercitar a contração chunk -> documento.
        ranked = [gold[0], gold[0], *gold[1:]]
        return [_Hit(document_id=item) for item in ranked[:limit]]


def test_retrieval_benchmark_is_governed_and_catalog_resolvable():
    suite = load_retrieval_benchmark(BENCHMARK)
    validation = validate_retrieval_benchmark_against_catalog(suite, CATALOG)

    assert len(suite.cases) == 30
    assert Counter(case.category for case in suite.cases) == Counter(
        {
            RetrievalCategory.NORMATIVE: 15,
            RetrievalCategory.CROSS_SOURCE: 8,
            RetrievalCategory.METHODOLOGY: 6,
            RetrievalCategory.CONTROL_EXTERNAL: 1,
        }
    )
    assert validation["status"] == "PASS"
    assert validation["cases"] == 30
    assert validation["freshness_sensitive_cases"] == 3
    assert all(case.gold_document_ids for case in suite.cases)
    assert all(case.expected_scopes for case in suite.cases)


def test_retrieval_evaluation_collapses_duplicate_chunks_to_documents():
    suite = load_retrieval_benchmark(BENCHMARK)
    retriever = _PerfectDocumentRetriever(
        {case.question: case.gold_document_ids for case in suite.cases}
    )

    result = evaluate_retrieval_benchmark(suite, retriever, k=5, governed=True)

    assert result["summary"]["cases"] == 30
    assert result["summary"]["hit_rate_at_5"] == 1.0
    assert result["summary"]["mean_document_recall_at_5"] == 1.0
    assert result["summary"]["mrr"] == 1.0
    assert result["summary"]["map_at_5"] == 1.0
    assert all(
        len(row["retrieved_document_ids"]) == len(set(row["retrieved_document_ids"]))
        for row in result["cases"]
    )


def test_retrieval_benchmark_covers_governed_corpus_dimensions():
    suite = load_retrieval_benchmark(BENCHMARK)
    scopes = {scope.value for case in suite.cases for scope in case.expected_scopes}
    trails = {trail for case in suite.cases for trail in case.expected_trails}

    assert scopes == {"cpgf_core", "methodology", "control_external"}
    assert {"T02", "T03", "T04", "T05", "T07", "T08", "T09"}.issubset(trails)
    assert "T01" not in trails
    assert "T06" not in trails
