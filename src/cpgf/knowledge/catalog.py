from __future__ import annotations

import json
from pathlib import Path, PurePosixPath

from pydantic import TypeAdapter

from .models import DocumentSpec

_DOCUMENT_LIST = TypeAdapter(list[DocumentSpec])


def _safe_include(base: Path, value: str) -> Path:
    normalized = value.replace("\\", "/").strip()
    relative = PurePosixPath(normalized)
    if not normalized or relative.is_absolute() or any(part in {"", ".", ".."} for part in relative.parts):
        raise ValueError("include do catálogo deve permanecer dentro do diretório do catálogo")
    return base / Path(*relative.parts)


def _load_payload(path: Path, visited: set[Path]) -> list[dict[str, object]]:
    path = path.resolve()
    if path in visited:
        raise ValueError(f"Ciclo de includes no catálogo Knowledge: {path}")
    visited.add(path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, list):
        return payload
    if not isinstance(payload, dict):
        raise ValueError("Catálogo Knowledge deve ser objeto ou lista")
    documents = list(payload.get("documents", []))
    for include in payload.get("includes", []):
        include_path = _safe_include(path.parent, str(include))
        documents.extend(_load_payload(include_path, visited))
    return documents


def load_source_catalog(path: Path) -> list[DocumentSpec]:
    payload = _load_payload(Path(path), set())
    documents = _DOCUMENT_LIST.validate_python(payload)
    ids = [item.document_id for item in documents]
    if len(ids) != len(set(ids)):
        raise ValueError("Catálogo Knowledge contém document_id duplicado")
    paths = [item.source_relative_path for item in documents if item.source_relative_path]
    if len(paths) != len(set(paths)):
        raise ValueError("Catálogo Knowledge contém caminho de fonte duplicado")
    return documents
