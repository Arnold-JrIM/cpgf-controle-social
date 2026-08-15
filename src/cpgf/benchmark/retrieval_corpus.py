from __future__ import annotations

from collections.abc import Iterable

from .retrieval import RetrievalBenchmarkSuite


def validate_retrieval_corpus_coverage(
    suite: RetrievalBenchmarkSuite,
    available_document_ids: Iterable[str],
) -> dict[str, object]:
    """Valida se todos os documentos-gabarito têm conteúdo recuperável no corpus local."""
    available = {str(document_id) for document_id in available_document_ids}
    gold = {
        document_id
        for case in suite.cases
        for document_id in case.gold_document_ids
    }
    missing_gold = sorted(gold - available)
    if missing_gold:
        raise ValueError(
            "Corpus local incompleto para o benchmark: documentos-gabarito sem chunks: "
            + ", ".join(missing_gold)
        )

    return {
        "status": "PASS",
        "benchmark_cases": len(suite.cases),
        "gold_documents": len(gold),
        "gold_documents_with_chunks": len(gold),
        "available_documents_with_chunks": len(available),
        "missing_gold_documents": [],
    }
