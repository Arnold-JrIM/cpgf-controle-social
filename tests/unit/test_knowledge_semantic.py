from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pandas as pd

from cpgf.knowledge import (
    HybridKnowledgeRetriever,
    LexicalKnowledgeRetriever,
    OpenAIEmbeddingProvider,
    SemanticKnowledgeRetriever,
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


def test_openai_embedding_provider_uses_explicit_float_encoding():
    calls: list[dict[str, object]] = []

    class FakeEmbeddings:
        def create(self, **kwargs: object) -> object:
            calls.append(kwargs)
            return SimpleNamespace(
                data=[SimpleNamespace(embedding=[1.0, 0.0]), SimpleNamespace(embedding=[0.0, 1.0])]
            )

    fake_client = SimpleNamespace(embeddings=FakeEmbeddings())
    provider = OpenAIEmbeddingProvider(model="text-embedding-3-small", dimensions=2, client=fake_client)
    vectors = provider.embed_texts(["um", "dois"])

    assert vectors.shape == (2, 2)
    assert calls[0]["model"] == "text-embedding-3-small"
    assert calls[0]["dimensions"] == 2
    assert calls[0]["encoding_format"] == "float"
