from __future__ import annotations

import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from cpgf.version import KNOWLEDGE_VERSION

from .catalog import load_source_catalog
from .loader import document_page_count, load_document, sha256_file
from .models import DocumentSpec
from .splitter import split_sections

_LIST_COLUMNS = ("authors", "trails", "supports_trails", "related_trails")


def _document_row(
    spec: DocumentSpec,
    source_path: Path | None,
    source_sha256: str | None,
    *,
    source_pages: int | None,
    section_count: int,
    chunk_count: int,
    ingestion_status: str,
) -> dict[str, object]:
    payload = spec.model_dump(mode="json")
    for key in _LIST_COLUMNS:
        payload[key] = json.dumps(payload[key], ensure_ascii=False)
    payload["source_relative_path"] = spec.source_relative_path
    payload["ingestion_status"] = ingestion_status
    payload["source_sha256"] = source_sha256
    payload["source_bytes"] = source_path.stat().st_size if source_path is not None else None
    payload["source_pages"] = source_pages
    payload["section_count"] = section_count
    payload["chunk_count"] = chunk_count
    return payload


def _chunk_row(chunk: object) -> dict[str, object]:
    payload = chunk.model_dump(mode="json")
    for key in ("supports_trails", "related_trails"):
        payload[key] = json.dumps(payload[key], ensure_ascii=False)
    return payload


def _contract_mismatches(
    spec: DocumentSpec,
    *,
    source_sha256: str,
    source_bytes: int,
    source_pages: int,
) -> list[dict[str, object]]:
    mismatches: list[dict[str, object]] = []
    for field, expected, actual in (
        ("sha256", spec.expected_sha256, source_sha256),
        ("bytes", spec.expected_bytes, source_bytes),
        ("pages", spec.expected_pages, source_pages),
    ):
        if expected is not None and expected != actual:
            mismatches.append(
                {
                    "document_id": spec.document_id,
                    "field": field,
                    "expected": expected,
                    "actual": actual,
                }
            )
    return mismatches


def build_knowledge_bundle(
    catalog_path: Path,
    source_root: Path,
    output_dir: Path,
    *,
    require_all_sources: bool = False,
    require_text_sources: bool = False,
    verify_source_contract: bool = True,
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
    no_text_sources: list[str] = []
    source_contract_mismatches: list[dict[str, object]] = []

    for spec in documents:
        if not spec.active:
            continue
        source_path: Path | None = None
        source_sha256: str | None = None
        source_pages: int | None = None
        sections = []
        chunks = []
        relative_path = spec.source_relative_path

        if relative_path:
            candidate = source_root / relative_path
            if candidate.is_file():
                source_path = candidate
                source_sha256 = sha256_file(candidate)
                source_pages = document_page_count(candidate)
                mismatches = _contract_mismatches(
                    spec,
                    source_sha256=source_sha256,
                    source_bytes=candidate.stat().st_size,
                    source_pages=source_pages,
                )
                source_contract_mismatches.extend(mismatches)
                if verify_source_contract and mismatches:
                    raise ValueError(f"Fonte divergiu do contrato: {mismatches}")
                if spec.ingest_content:
                    sections = load_document(candidate, spec.document_id)
                    chunks = split_sections(
                        spec,
                        sections,
                        source_sha256=source_sha256,
                        max_chars=max_chars,
                        overlap_chars=overlap_chars,
                    )
            else:
                missing_sources.append(spec.document_id)

        if source_path is None:
            ingestion_status = "METADATA_ONLY"
        elif not spec.ingest_content:
            ingestion_status = "AVAILABLE_NOT_INGESTED"
        elif sections:
            ingestion_status = "AVAILABLE"
        else:
            ingestion_status = "AVAILABLE_NO_TEXT"
            no_text_sources.append(spec.document_id)

        document_rows.append(
            _document_row(
                spec,
                source_path,
                source_sha256,
                source_pages=source_pages,
                section_count=len(sections),
                chunk_count=len(chunks),
                ingestion_status=ingestion_status,
            )
        )
        chunk_rows.extend(_chunk_row(chunk) for chunk in chunks)

    if require_all_sources and missing_sources:
        raise FileNotFoundError(f"Fontes Knowledge ausentes: {sorted(missing_sources)}")
    if require_text_sources:
        default_no_text = sorted(
            item.document_id
            for item in documents
            if item.active and item.retrieval_default and item.document_id in no_text_sources
        )
        if default_no_text:
            raise ValueError(f"Fontes padrão sem texto extraível: {default_no_text}")

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
                "scope",
                "temporal_status",
                "retrieval_default",
                "supports_trails",
                "related_trails",
                "citation",
                "source_url",
                "source_sha256",
            ]
        )

    documents_path = output_dir / "documents.parquet"
    chunks_path = output_dir / "chunks.parquet"
    documents_df.to_parquet(documents_path, index=False, compression="zstd")
    chunks_df.to_parquet(chunks_path, index=False, compression="zstd")

    status_counts = Counter(documents_df["ingestion_status"].astype(str))
    scope_counts = Counter(documents_df["scope"].astype(str))
    temporal_counts = Counter(documents_df["temporal_status"].astype(str))
    authority_counts = Counter(documents_df["authority_level"].astype(str))
    manifest = {
        "knowledge_version": KNOWLEDGE_VERSION,
        "created_at_utc": datetime.now(UTC).isoformat(),
        "catalog_path": str(catalog_path),
        "catalog_sha256": sha256_file(catalog_path),
        "documents": int(len(documents_df)),
        "documents_available": int(
            status_counts.get("AVAILABLE", 0)
            + status_counts.get("AVAILABLE_NO_TEXT", 0)
            + status_counts.get("AVAILABLE_NOT_INGESTED", 0)
        ),
        "documents_available_no_text": int(status_counts.get("AVAILABLE_NO_TEXT", 0)),
        "documents_available_not_ingested": int(status_counts.get("AVAILABLE_NOT_INGESTED", 0)),
        "documents_metadata_only": int(status_counts.get("METADATA_ONLY", 0)),
        "documents_retrieval_default": int(documents_df["retrieval_default"].astype(bool).sum()),
        "chunks": int(len(chunks_df)),
        "chunks_retrieval_default": (
            int(chunks_df["retrieval_default"].astype(bool).sum()) if not chunks_df.empty else 0
        ),
        "missing_sources": sorted(missing_sources),
        "no_text_sources": sorted(no_text_sources),
        "source_contract_mismatches": source_contract_mismatches,
        "counts_by_scope": dict(sorted(scope_counts.items())),
        "counts_by_temporal_status": dict(sorted(temporal_counts.items())),
        "counts_by_authority_level": dict(sorted(authority_counts.items())),
        "chunking": {"max_chars": max_chars, "overlap_chars": overlap_chars},
        "retrieval": {
            "baseline": "lexical",
            "default_only": True,
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
            "A publicação de fontes originais ou chunks depende da política de distribuição de cada documento. "
            "O catálogo distingue conteúdo oficial, licença aberta, metadata_only e material do projeto."
        ),
    }
    (output_dir / "knowledge_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return manifest
