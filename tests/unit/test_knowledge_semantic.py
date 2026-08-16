from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd

from cpgf.knowledge import (
    HybridKnowledgeRetriever,
    LexicalKnowledgeRetriever,
    OpenAIEmbeddingProvider,
    SemanticKnowledgeRetriever,
    build_semantic_index,
    persist_semantic_index,
    validate_semantic_index,
)


def _chunks() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "chunk_id": "c1",
                "document_id": "norma",
                "text": "Suprimento de fundos exige prestação de contas.",
                "page": 1,
                "citation": "ÓRGÃO. Norma.",
                "source_class": "normative",
                "authority_level": "primary_normative",
                "scope": "cpgf_core",
                "temporal_status": "current",
                "retrieval_default": True,
                "source_url": None,
            },
            {
                "chunk_id": "c2",
                "document_id": "artigo",
                "text": "Auditoria orientada por dados apoia a seleção de sinais.",
                "page": 2,
                "citation": "AUTOR. Artigo.",
                "source_class": "scientific",
                "authority_level": "scientific_peer_reviewed",
                "scope": "methodology",
                "temporal_status": "contextual",
                "retrieval_default": True,
                "source_url": None,
            },
            {
                "chunk_id": "c3",
                "document_id": "historico",
                "text": "Regra histórica revogada.",
                "page": 1,
                "citation": "ÓRGÃO. Histórico.",
                "source_class": "normative",
                "authority_level": "primary_normative",
                "scope": "historical",
                "temporal_status": "historical",
                "retrieval_default": False,
                "source_url": None,
            },
        ]
    )


class FakeEmbeddingProvider:
    model = "fake-embedding"
    dimensions = 2

    def embed_texts(self, texts: list[str]) -> np.ndarray:
        vectors = []
        for text in texts:
            lowered = text.lower()
            if "auditoria" in lowered or "analytics" in lowered:
                vectors.append([0.0, 1.0])
            elif "histórica" in lowered or "revogada" in lowered:
                vectors.append([0.8, 0.2])
            else:
                vectors.append([1.0, 0.0])
        return np.asarray(vectors, dtype=np.float32)


def _embeddings() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "chunk_id": ["c1", "c2", "c3"],
            "embedding": [[1.0, 0.0], [0.0, 1.0], [0.8, 0.2]],
        }
    )


def test_semantic_retrieval_preserves_governance_filters():
    retriever = SemanticKnowledgeRetriever(_chunks(), _embeddings(), FakeEmbeddingProvider())
    hits = retriever.search("adiantamento para despesas miúdas", limit=2)
    assert hits[0].document_id == "norma"
    assert hits[0].retrieval_method == "semantic"
    assert all(hit.document_id != "historico" for hit in hits)

    historical = retriever.search("regra histórica revogada", include_non_default=True)
    assert historical[0].document_id == "historico"


def test_hybrid_uses_rrf_and_keeps_method_explicit():
    chunks = _chunks()
    lexical = LexicalKnowledgeRetriever(chunks)
    semantic = SemanticKnowledgeRetriever(chunks, _embeddings(), FakeEmbeddingProvider())
    hybrid = HybridKnowledgeRetriever(lexical, semantic)

    hits = hybrid.search("suprimento analytics", limit=2)
    assert {hit.document_id for hit in hits} == {"norma", "artigo"}
    assert all(hit.retrieval_method == "hybrid" for hit in hits)
    assert len({hit.chunk_id for hit in hits}) == len(hits)


def test_semantic_index_must_cover_all_chunks():
    partial = _embeddings().iloc[:2].copy()
    try:
        SemanticKnowledgeRetriever(_chunks(), partial, FakeEmbeddingProvider())
    except ValueError as exc:
        assert "não cobre todos os chunks" in str(exc)
    else:
        raise AssertionError("Índice parcial deveria ser rejeitado")


def test_build_persist_and_validate_semantic_index(tmp_path: Path):
    chunks = _chunks()
    chunks_path = tmp_path / "chunks.parquet"
    chunks.to_parquet(chunks_path, index=False)
    provider = FakeEmbeddingProvider()
    index = build_semantic_index(chunks, provider, batch_size=2)
    manifest = persist_semantic_index(chunks_path, index, tmp_path, provider)
    validation = validate_semantic_index(chunks_path, tmp_path)

    assert manifest["knowledge_version"] == "1.2.0"
    assert manifest["chunks"] == 3
    assert manifest["dimensions"] == 2
    assert validation["status"] == "PASS"
    assert validation["chunks"] == 3


def test_openai_embedding_provider_uses_cache_and_explicit_float_encoding():
    calls: list[dict[str, object]] = []

    class FakeEmbeddings:
        def create(self, **kwargs: object) -> object:
            calls.append(kwargs)
            inputs = list(kwargs["input"])
            vectors = [[1.0, 0.0] if text == "um" else [0.0, 1.0] for text in inputs]
            return SimpleNamespace(data=[SimpleNamespace(embedding=vector) for vector in vectors])

    fake_client = SimpleNamespace(embeddings=FakeEmbeddings())
    provider = OpenAIEmbeddingProvider(model="text-embedding-3-small", dimensions=2, client=fake_client)
    vectors = provider.embed_texts(["um", "dois"])
    cached = provider.embed_texts(["um"])

    assert vectors.shape == (2, 2)
    assert cached.shape == (1, 2)
    assert len(calls) == 1
    assert calls[0]["model"] == "text-embedding-3-small"
    assert calls[0]["dimensions"] == 2
    assert calls[0]["encoding_format"] == "float"
    assert provider.external_request_count == 1
    assert provider.embedded_text_count == 2
