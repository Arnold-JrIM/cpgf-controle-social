from __future__ import annotations

import math
import re
import unicodedata
from collections import Counter

import pandas as pd

from .models import AuthorityLevel, SearchHit, SourceClass

_TOKEN = re.compile(r"[a-z0-9]{2,}")


def tokenize(text: str) -> list[str]:
    normalized = unicodedata.normalize("NFKD", text.lower())
    ascii_text = "".join(char for char in normalized if not unicodedata.combining(char))
    return _TOKEN.findall(ascii_text)


class LexicalKnowledgeRetriever:
    """Baseline determinística para validar o corpus antes de embeddings."""

    def __init__(self, chunks: pd.DataFrame):
        required = {
            "chunk_id",
            "document_id",
            "text",
            "page",
            "citation",
            "source_class",
            "authority_level",
            "source_url",
        }
        missing = required - set(chunks.columns)
        if missing:
            raise ValueError(f"Chunks sem colunas obrigatórias: {sorted(missing)}")
        self._chunks = chunks.reset_index(drop=True).copy()
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
    ) -> list[SearchHit]:
        if not query.strip():
            raise ValueError("Consulta vazia")
        if not 1 <= limit <= 20:
            raise ValueError("limit deve estar entre 1 e 20")
        query_tokens = Counter(tokenize(query))
        scored: list[tuple[float, int]] = []
        for index, tokens in enumerate(self._tokens):
            row = self._chunks.iloc[index]
            if source_classes and str(row["source_class"]) not in source_classes:
                continue
            score = 0.0
            for token, query_tf in query_tokens.items():
                if token in tokens:
                    score += (1.0 + math.log(tokens[token])) * self._idf.get(token, 1.0) * query_tf
            if score > 0:
                scored.append((score, index))
        scored.sort(key=lambda item: (-item[0], str(self._chunks.iloc[item[1]]["chunk_id"])))
        hits = []
        for score, index in scored[:limit]:
            row = self._chunks.iloc[index]
            page = row["page"]
            hits.append(
                SearchHit(
                    chunk_id=str(row["chunk_id"]),
                    document_id=str(row["document_id"]),
                    score=float(score),
                    text=str(row["text"]),
                    page=None if pd.isna(page) else int(page),
                    citation=str(row["citation"]),
                    source_class=SourceClass(str(row["source_class"])),
                    authority_level=AuthorityLevel(str(row["authority_level"])),
                    source_url=None if pd.isna(row["source_url"]) else str(row["source_url"]),
                )
            )
        return hits
