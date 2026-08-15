from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath

import pandas as pd

from cpgf.version import KNOWLEDGE_VERSION

from .embeddings import EmbeddingProvider
from .loader import sha256_file


def build_semantic_index(
    chunks: pd.DataFrame,
    provider: EmbeddingProvider,
    *,
    batch_size: int = 64,
) -> pd.DataFrame:
    if not {"chunk_id", "document_id", "text"}.issubset(chunks.columns):
        raise ValueError("Chunks requerem chunk_id, document_id e text")
    if chunks.empty:
        raise ValueError("Não há chunks para indexar")
    if not 1 <= batch_size <= 256:
        raise ValueError("batch_size deve estar entre 1 e 256")
    if chunks["chunk_id"].astype(str).duplicated().any():
        raise ValueError("chunk_id duplicado no corpus")

    rows: list[dict[str, object]] = []
    for start in range(0, len(chunks), batch_size):
        batch = chunks.iloc[start : start + batch_size]
        texts = batch["text"].astype(str).tolist()
        vectors = provider.embed_texts(texts)
        if vectors.shape[0] != len(batch):
            raise ValueError("Provider retornou quantidade divergente de embeddings")
        for offset, (_, row) in enumerate(batch.iterrows()):
            rows.append(
                {
                    "chunk_id": str(row["chunk_id"]),
                    "document_id": str(row["document_id"]),
                    "embedding": vectors[offset].astype("float32").tolist(),
                }
            )
    return pd.DataFrame(rows)


def persist_semantic_index(
    chunks_path: Path,
    index: pd.DataFrame,
    output_dir: Path,
    provider: EmbeddingProvider,
) -> dict[str, object]:
    chunks_path = Path(chunks_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    index_path = output_dir / "embeddings.parquet"
    index.to_parquet(index_path, index=False, compression="zstd")
    dimensions = len(index.iloc[0]["embedding"]) if not index.empty else 0
    manifest = {
        "knowledge_version": KNOWLEDGE_VERSION,
        "created_at_utc": datetime.now(UTC).isoformat(),
        "model": provider.model,
        "dimensions": int(dimensions),
        "chunks": int(len(index)),
        "source_chunks_sha256": sha256_file(chunks_path),
        "artifact": {
            "path": "embeddings.parquet",
            "sha256": sha256_file(index_path),
            "bytes": index_path.stat().st_size,
        },
        "governance": {
            "retrieval_filters_remain_authoritative": True,
            "llm_enabled": False,
            "index_distribution": "local_artifact_not_committed",
            "external_embedding_provider_is_opt_in": True,
        },
    }
    (output_dir / "embeddings_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return manifest


def validate_semantic_index(chunks_path: Path, index_dir: Path) -> dict[str, object]:
    chunks_path = Path(chunks_path)
    index_dir = Path(index_dir)
    manifest_path = index_dir / "embeddings_manifest.json"
    if not chunks_path.is_file() or not manifest_path.is_file():
        raise FileNotFoundError("chunks.parquet ou embeddings_manifest.json ausente")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("knowledge_version") != KNOWLEDGE_VERSION:
        raise ValueError("Versão do índice semântico difere do Knowledge atual")
    if manifest.get("source_chunks_sha256") != sha256_file(chunks_path):
        raise ValueError("Índice semântico foi construído para outro chunks.parquet")

    relative = str(manifest.get("artifact", {}).get("path", ""))
    artifact_path = PurePosixPath(relative)
    if not relative or artifact_path.is_absolute() or ".." in artifact_path.parts:
        raise ValueError("Caminho do artefato semântico inválido")
    index_path = index_dir.joinpath(*artifact_path.parts)
    if not index_path.is_file():
        raise FileNotFoundError("embeddings.parquet ausente")
    artifact = manifest["artifact"]
    if artifact.get("sha256") != sha256_file(index_path):
        raise ValueError("Hash do índice semântico divergiu do manifesto")
    if int(artifact.get("bytes", -1)) != index_path.stat().st_size:
        raise ValueError("Tamanho do índice semântico divergiu do manifesto")

    chunks = pd.read_parquet(chunks_path, columns=["chunk_id", "document_id"])
    index = pd.read_parquet(index_path)
    if not {"chunk_id", "document_id", "embedding"}.issubset(index.columns):
        raise ValueError("Índice semântico sem colunas obrigatórias")
    if index["chunk_id"].astype(str).duplicated().any():
        raise ValueError("chunk_id duplicado no índice semântico")
    if int(manifest.get("chunks", -1)) != len(index) or len(index) != len(chunks):
        raise ValueError("Cobertura do índice semântico divergiu do corpus")

    expected = dict(zip(chunks["chunk_id"].astype(str), chunks["document_id"].astype(str), strict=True))
    actual = dict(zip(index["chunk_id"].astype(str), index["document_id"].astype(str), strict=True))
    if expected != actual:
        raise ValueError("Identidade chunk/documento do índice divergiu do corpus")
    dimensions = {len(vector) for vector in index["embedding"]}
    if dimensions != {int(manifest.get("dimensions", 0))}:
        raise ValueError("Dimensionalidade do índice semântico divergiu do manifesto")

    return {
        "status": "PASS",
        "knowledge_version": KNOWLEDGE_VERSION,
        "model": str(manifest.get("model")),
        "dimensions": int(manifest["dimensions"]),
        "chunks": int(len(index)),
        "index_sha256": str(artifact["sha256"]),
    }
