from __future__ import annotations

import hashlib

from .models import DocumentSpec, KnowledgeChunk, LoadedSection


def _windows(text: str, max_chars: int, overlap_chars: int) -> list[str]:
    if len(text) <= max_chars:
        return [text]
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(len(text), start + max_chars)
        if end < len(text):
            boundary = text.rfind("\n\n", start, end)
            if boundary <= start + max_chars // 2:
                boundary = text.rfind(". ", start, end)
                if boundary > start + max_chars // 2:
                    boundary += 1
            if boundary > start + max_chars // 2:
                end = boundary
        part = text[start:end].strip()
        if part:
            chunks.append(part)
        if end >= len(text):
            break
        start = max(end - overlap_chars, start + 1)
    return chunks


def split_sections(
    spec: DocumentSpec,
    sections: list[LoadedSection],
    *,
    source_sha256: str | None,
    max_chars: int = 1800,
    overlap_chars: int = 180,
) -> list[KnowledgeChunk]:
    if max_chars < 300:
        raise ValueError("max_chars deve ser >= 300")
    if overlap_chars < 0 or overlap_chars >= max_chars:
        raise ValueError("overlap_chars deve estar entre 0 e max_chars-1")
    output: list[KnowledgeChunk] = []
    ordinal = 0
    for section in sections:
        for text in _windows(section.text, max_chars, overlap_chars):
            raw_id = f"{spec.document_id}|{section.page}|{ordinal}|{text}".encode("utf-8")
            chunk_id = hashlib.sha256(raw_id).hexdigest()[:24]
            output.append(
                KnowledgeChunk(
                    chunk_id=chunk_id,
                    document_id=spec.document_id,
                    text=text,
                    ordinal=ordinal,
                    page=section.page,
                    section=section.section,
                    source_class=spec.source_class,
                    authority_level=spec.authority_level,
                    citation=spec.citation,
                    source_url=spec.source_url,
                    source_sha256=source_sha256,
                )
            )
            ordinal += 1
    return output
