from __future__ import annotations

import math
import re
import unicodedata
from collections import Counter

import numpy as np
import pandas as pd

from .embeddings import EmbeddingProvider, normalize_embeddings
from .models import AuthorityLevel, CorpusScope, SearchHit, SourceClass, TemporalStatus

_TOKEN = re.compile(r"[a-z0-9]{2,}")
_REQUIRED_COLUMNS = {
    "chunk_id",
    "document_id",
    "text",
    "page",
    "citation",
    "source_class",
    "authority_level",
    "scope",
    "temporal_status",
    "retrieval_default",
    "source_url",
}


def tokenize(text: str) -> list[str]:
    normalized = unicodedata.normalize("NFKD", text.lower())
    ascii_text = "".join(char for char in normalized if not unicodedata.combining(char))
    return _TOKEN.findall(ascii_text)


def _validate_chunks(chunks: pd.DataFrame) -> pd.DataFrame:
    missing = _REQUIRED_COLUMNS - set(chunks.columns)
    if missing:
        raise ValueError(f"Chunks sem colunas obrigatórias: {sorted(missing)}")
    if chunks["chunk_id"].astype(str).duplicated().any():
        raise ValueError("chunk_id duplicado no corpus")
    return chunks.reset_index(drop=True).copy()


def _row_allowed(
    row: pd.Series,
    *,
    source_classes: set[str] | None,
    scopes: set[str] | None,
    temporal_statuses: set[str] | None,
    document_ids: set[str] | None,
    include_non_default: bool,
) -> bool:
    if not include_non_default and not bool(row["retrieval_default"]):
        return False
    if source_classes and str(row["source_class"]) not in source_classes:
        return False
    if scopes and str(row["scope"]) not in scopes:
        return False
    if temporal_statuses and str(row["temporal_status"]) not in temporal_statuses:
        return False
    if document_ids and str(row["document_id"]) not in document_ids:
        return False
    return True


def _hit(row: pd.Series, score: float, method: str) -> SearchHit:
    page = row["page"]
    return SearchHit(
        chunk_id=str(row["chunk_id"]),
        document_id=str(row["document_id"]),
        score=float(score),
        text=str(row["text"]),
        page=None if pd.isna(page) else int(page),
        citation=str(row["citation"]),
        source_class=SourceClass(str(row["source_class"])),
        authority_level=AuthorityLevel(str(row["authority_level"])),
        scope=CorpusScope(str(row["scope"])),
        temporal_status=TemporalStatus(str(row["temporal_status"])),
        retrieval_default=bool(row["retrieval_default"]),
        source_url=None if pd.isna(row["source_url"]) else str(row["source_url"]),
        retrieval_method=method,
    )


class LexicalKnowledgeRetriever:
    """Baseline determinística do corpus governado."""

    def __init__(self, chunks: pd.DataFrame):
        self._chunks = _validate_chunks(chunks)
        self._tokens = [Counter(tokenize(str(text))) for text in self._chunks["text"]]
        document_frequency: Counter[str] = Counter()
        for tokens in self._tokens:
            document_frequency.update(tokens.keys())
        total = max(len(self._tokens), 1)
        self._idf = {
            token: math.log((1 + total) / (1 + frequency)) + 1.0
            for token, frequency in document_frequency.items()
        }

    def search(
        self,
        query: str,
        *,
        limit: int = 5,
        source_classes: set[str] | None = None,
        scopes: set[str] | None = None,
        temporal_statuses: set[str] | None = None,
        document_ids: set[str] | None = None,
        include_non_default: bool = False,
    ) -> list[SearchHit]:
        if not query.strip():
            raise ValueError("Consulta vazia")
        if not 1 <= limit <= 20:
            raise ValueError("limit deve estar entre 1 e 20")
        query_tokens = Counter(tokenize(query))
        scored: list[tuple[float, int]] = []
        for index, tokens in enumerate(self._tokens):
            row = self._chunks.iloc[index]
            if not _row_allowed(
                row,
                source_classes=source_classes,
                scopes=scopes,
                temporal_statuses=temporal_statuses,
                document_ids=document_ids,
                include_non_default=include_non_default,
            ):
                continue
            score = 0.0
            for token, query_tf in query_tokens.items():
                if token in tokens:
                    score += (1.0 + math.log(tokens[token])) * self._idf.get(token, 1.0) * query_tf
            if score > 0:
                scored.append((score, index))
        scored.sort(key=lambda item: (-item[0], str(self._chunks.iloc[item[1]]["chunk_id"])))
        return [_hit(self._chunks.iloc[index], score, "lexical") for score, index in scored[:limit]]


class SemanticKnowledgeRetriever:
    """Recuperação por similaridade cosseno sobre índice vetorial explicitamente fornecido."""

    def __init__(
        self,
        chunks: pd.DataFrame,
        embeddings: pd.DataFrame,
        provider: EmbeddingProvider,
    ):
        self._chunks = _validate_chunks(chunks)
        if not {"chunk_id", "embedding"}.issubset(embeddings.columns):
            raise ValueError("Índice semântico requer chunk_id e embedding")
        if embeddings["chunk_id"].astype(str).duplicated().any():
            raise ValueError("chunk_id duplicado no índice semântico")
        vectors_by_id = {
            str(row["chunk_id"]): np.asarray(row["embedding"], dtype=np.float32)
            for _, row in embeddings.iterrows()
        }
        missing = [str(chunk_id) for chunk_id in self._chunks["chunk_id"] if str(chunk_id) not in vectors_by_id]
        if missing:
            raise ValueError(f"Índice semântico não cobre todos os chunks: {missing[:5]}")
        dimensions = {int(vector.shape[0]) for vector in vectors_by_id.values() if vector.ndim == 1}
        if len(dimensions) != 1 or any(vector.ndim != 1 for vector in vectors_by_id.values()):
            raise ValueError("Embeddings devem ter dimensionalidade vetorial única")
        self._vectors = normalize_embeddings(
            np.vstack([vectors_by_id[str(chunk_id)] for chunk_id in self._chunks["chunk_id"]])
        )
        self._provider = provider

    def search(
        self,
        query: str,
        *,
        limit: int = 5,
        source_classes: set[str] | None = None,
        scopes: set[str] | None = None,
        temporal_statuses: set[str] | None = None,
        document_ids: set[str] | None = None,
        include_non_default: bool = False,
    ) -> list[SearchHit]:
        if not query.strip():
            raise ValueError("Consulta vazia")
        if not 1 <= limit <= 20:
            raise ValueError("limit deve estar entre 1 e 20")
        query_vector = normalize_embeddings(self._provider.embed_texts([query]))[0]
        if query_vector.shape[0] != self._vectors.shape[1]:
            raise ValueError("Dimensão do embedding da consulta difere do índice")
        similarities = self._vectors @ query_vector
        scored: list[tuple[float, int]] = []
        for index, score in enumerate(similarities.tolist()):
            row = self._chunks.iloc[index]
            if score <= 0 or not _row_allowed(
                row,
                source_classes=source_classes,
                scopes=scopes,
                temporal_statuses=temporal_statuses,
                document_ids=document_ids,
                include_non_default=include_non_default,
            ):
                continue
            scored.append((float(score), index))
        scored.sort(key=lambda item: (-item[0], str(self._chunks.iloc[item[1]]["chunk_id"])))
        return [_hit(self._chunks.iloc[index], score, "semantic") for score, index in scored[:limit]]


class HybridKnowledgeRetriever:
    """Fusão RRF de rankings lexical e semântico, sem misturar escalas de score."""

    def __init__(
        self,
        lexical: LexicalKnowledgeRetriever,
        semantic: SemanticKnowledgeRetriever,
        *,
        rrf_k: int = 60,
    ):
        if rrf_k <= 0:
            raise ValueError("rrf_k deve ser positivo")
        self._lexical = lexical
        self._semantic = semantic
        self._rrf_k = rrf_k

    def search(self, query: str, *, limit: int = 5, **filters: object) -> list[SearchHit]:
        if not 1 <= limit <= 20:
            raise ValueError("limit deve estar entre 1 e 20")
        candidate_limit = min(20, max(limit * 4, limit))
        lexical_hits = self._lexical.search(query, limit=candidate_limit, **filters)
        semantic_hits = self._semantic.search(query, limit=candidate_limit, **filters)
        fused: dict[str, float] = {}
        representative: dict[str, SearchHit] = {}
        for hits in (lexical_hits, semantic_hits):
            for rank, hit in enumerate(hits, start=1):
                fused[hit.chunk_id] = fused.get(hit.chunk_id, 0.0) + 1.0 / (self._rrf_k + rank)
                representative.setdefault(hit.chunk_id, hit)
        ordered = sorted(fused.items(), key=lambda item: (-item[1], item[0]))[:limit]
        return [
            representative[chunk_id].model_copy(
                update={"score": float(score), "retrieval_method": "hybrid"}
            )
            for chunk_id, score in ordered
        ]
