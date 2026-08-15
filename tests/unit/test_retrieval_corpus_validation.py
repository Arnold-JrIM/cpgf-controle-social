from pathlib import Path

import pytest

from cpgf.benchmark import (
    load_retrieval_benchmark,
    validate_retrieval_corpus_coverage,
)

BENCHMARK = Path("data/benchmarks/knowledge_retrieval_v1_0_0.csv")


def _gold_documents() -> set[str]:
    suite = load_retrieval_benchmark(BENCHMARK)
    return {
        document_id
        for case in suite.cases
        for document_id in case.gold_document_ids
    }


def test_corpus_validation_requires_every_gold_document_to_have_chunks():
    suite = load_retrieval_benchmark(BENCHMARK)
    gold = _gold_documents()

    result = validate_retrieval_corpus_coverage(suite, gold | {"documento-extra"})

    assert result["status"] == "PASS"
    assert result["gold_documents"] == 24
    assert result["gold_documents_with_chunks"] == 24
    assert result["missing_gold_documents"] == []


def test_corpus_validation_fails_when_one_gold_document_is_missing():
    suite = load_retrieval_benchmark(BENCHMARK)
    gold = _gold_documents()
    missing = sorted(gold)[0]

    with pytest.raises(ValueError, match="documentos-gabarito sem chunks") as excinfo:
        validate_retrieval_corpus_coverage(suite, gold - {missing})

    assert missing in str(excinfo.value)
