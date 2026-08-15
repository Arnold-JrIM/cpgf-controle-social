from __future__ import annotations

from dataclasses import dataclass
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

    def _client(self) -> object:
        if self.client is None:
            from openai import OpenAI

            self.client = OpenAI()
        return self.client

    def embed_texts(self, texts: list[str]) -> np.ndarray:
        if not texts or any(not text.strip() for text in texts):
            raise ValueError("Textos para embedding devem ser não vazios")
        client = self._client()
        kwargs: dict[str, object] = {
            "model": self.model,
            "input": texts,
            "encoding_format": "float",
        }
        if self.dimensions is not None:
            kwargs["dimensions"] = self.dimensions
        response = client.embeddings.create(**kwargs)
        vectors = np.asarray([item.embedding for item in response.data], dtype=np.float32)
        if vectors.ndim != 2 or vectors.shape[0] != len(texts):
            raise ValueError("Resposta de embeddings incompatível com os textos enviados")
        return vectors


def normalize_embeddings(vectors: np.ndarray) -> np.ndarray:
    matrix = np.asarray(vectors, dtype=np.float32)
    if matrix.ndim != 2 or matrix.shape[0] == 0 or matrix.shape[1] == 0:
        raise ValueError("Matriz de embeddings inválida")
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    if np.any(norms == 0):
        raise ValueError("Embedding com norma zero")
    return matrix / norms
