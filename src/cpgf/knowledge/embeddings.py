from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

import numpy as np


class EmbeddingProvider(Protocol):
    model: str
    dimensions: int | None

    def embed_texts(self, texts: list[str]) -> np.ndarray: ...


@dataclass
class OpenAIEmbeddingProvider:
    """Provider explícito e opt-in para embeddings do Knowledge."""

    model: str = "text-embedding-3-small"
    dimensions: int | None = 768
    client: object | None = None
    cache_enabled: bool = True
    _cache: dict[str, np.ndarray] = field(default_factory=dict, init=False, repr=False)
    external_request_count: int = field(default=0, init=False)
    embedded_text_count: int = field(default=0, init=False)

    def _client(self) -> object:
        if self.client is None:
            from openai import OpenAI

            self.client = OpenAI()
        return self.client

    def embed_texts(self, texts: list[str]) -> np.ndarray:
        if not texts or any(not text.strip() for text in texts):
            raise ValueError("Textos para embedding devem ser não vazios")

        missing: list[str] = []
        seen_missing: set[str] = set()
        for text in texts:
            if self.cache_enabled and text in self._cache:
                continue
            if text not in seen_missing:
                missing.append(text)
                seen_missing.add(text)

        if missing:
            client = self._client()
            kwargs: dict[str, object] = {
                "model": self.model,
                "input": missing,
                "encoding_format": "float",
            }
            if self.dimensions is not None:
                kwargs["dimensions"] = self.dimensions
            response = client.embeddings.create(**kwargs)
            vectors = np.asarray([item.embedding for item in response.data], dtype=np.float32)
            if vectors.ndim != 2 or vectors.shape[0] != len(missing):
                raise ValueError("Resposta de embeddings incompatível com os textos enviados")
            self.external_request_count += 1
            self.embedded_text_count += len(missing)
            if self.cache_enabled:
                for text, vector in zip(missing, vectors, strict=True):
                    self._cache[text] = vector.copy()
            else:
                if len(texts) != len(missing):
                    raise RuntimeError("Cache desabilitado com entradas duplicadas não é suportado")
                return vectors

        if not self.cache_enabled:
            raise RuntimeError("Provider sem cache não produziu embeddings")
        return np.vstack([self._cache[text] for text in texts]).astype(np.float32)


def normalize_embeddings(vectors: np.ndarray) -> np.ndarray:
    matrix = np.asarray(vectors, dtype=np.float32)
    if matrix.ndim != 2 or matrix.shape[0] == 0 or matrix.shape[1] == 0:
        raise ValueError("Matriz de embeddings inválida")
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    if np.any(norms == 0):
        raise ValueError("Embedding com norma zero")
    return matrix / norms
