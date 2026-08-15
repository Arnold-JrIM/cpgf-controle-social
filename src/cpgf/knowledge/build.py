from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from cpgf.version import KNOWLEDGE_VERSION

from .catalog import load_source_catalog
from .loader import load_document, sha256_file
from .models import DocumentSpec
from .splitter import split_sections


def _document_row(spec: DocumentSpec, source_path: Path | None, source_sha256: str | None) -> dict[str, object]:
    payload = spec.model_dump(mode="json")
    payload["authors"] = json.dumps(payload["authors"], ensure_ascii=False)
    payload["trails"] = json.dumps(payload["trails"], ensure_ascii=False)
    payload["ingestion_status"] = "AVAILABLE" if source_path is not None else "METADATA_ONLY"
    payload["source_sha256"] = source_sha256
    payload["source_bytes"] = source_path.stat().st_size if source_path is not None else None
    return payload


def build_knowledge_bundle(
    catalog_path: Path,
    source_root: Path,
    output_dir: Path,
    *,
    require_all_sources: bool = False,
    max_chars: int = 1800,
    overlap_chars: int = 180,
) -> dict[str, object]:
    catalog_path = Path(catalog_path)
    source_root = Path(source_root)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    documents = load_source_catalog(catalog_path)

    document_rows: list[dict[str, object]] = []
    chunk_rows: list[dict[str, object]] = []
    missing_sources: list[str] = []
    for spec in documents:
        if not spec.active:
            continue
        source_path: Path | None = None
        source_sha256: str | None = None
        if spec.expected_filename:
            candidate = source_root / spec.expected_filename
            if candidate.is_file():
                source_path = candidate
                source_sha256 = sha256_file(candidate)
            else:
                missing_sources.append(spec.document_id)
        document_rows.append(_document_row(spec, source_path, source_sha256))
        if source_path is not None:
            sections = load_document(source_path, spec.document_id)
            chunks = split_sections(
                spec,
                sections,
                source_sha256=source_sha256,
                max_chars=max_chars,
                overlap_chars=overlap_chars,
            )
            chunk_rows.extend(chunk.model_dump(mode="json") for chunk in chunks)

    if require_all_sources and missing_sources:
        raise FileNotFoundError(f"Fontes Knowledge ausentes: {sorted(missing_sources)}")

    documents_df = pd.DataFrame(document_rows)
    chunks_df = pd.DataFrame(chunk_rows)
    if chunks_df.empty:
        chunks_df = pd.DataFrame(
            columns=[
                "chunk_id",
                "document_id",
                "text",
                "ordinal",
                "page",
                "section",
                "source_class",
                "authority_level",
                "citation",
                "source_url",
                "source_sha256",
            ]
        )
    documents_path = output_dir / "documents.parquet"
    chunks_path = output_dir / "chunks.parquet"
    documents_df.to_parquet(documents_path, index=False, compression="zstd")
    chunks_df.to_parquet(chunks_path, index=False, compression="zstd")

    manifest = {
        "knowledge_version": KNOWLEDGE_VERSION,
        "created_at_utc": datetime.now(UTC).isoformat(),
        "catalog_path": str(catalog_path),
        "catalog_sha256": sha256_file(catalog_path),
        "documents": int(len(documents_df)),
        "documents_available": int((documents_df["ingestion_status"] == "AVAILABLE").sum()),
        "documents_metadata_only": int((documents_df["ingestion_status"] == "METADATA_ONLY").sum()),
        "chunks": int(len(chunks_df)),
        "missing_sources": sorted(missing_sources),
        "chunking": {"max_chars": max_chars, "overlap_chars": overlap_chars},
        "retrieval": {
            "baseline": "lexical",
            "embeddings_enabled": False,
            "llm_enabled": False,
        },
        "artifacts": {
            "documents.parquet": {
                "sha256": sha256_file(documents_path),
                "bytes": documents_path.stat().st_size,
            },
            "chunks.parquet": {
                "sha256": sha256_file(chunks_path),
                "bytes": chunks_path.stat().st_size,
            },
        },
        "distribution_warning": (
            "A publicação de fontes originais ou chunks científicos depende da licença de cada documento. "
            "O catálogo distingue conteúdo oficial, licença aberta e metadata_only."
        ),
    }
    (output_dir / "knowledge_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return manifest
