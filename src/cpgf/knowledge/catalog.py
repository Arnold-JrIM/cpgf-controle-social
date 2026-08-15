from __future__ import annotations

import json
from pathlib import Path

from pydantic import TypeAdapter

from .models import DocumentSpec

_DOCUMENT_LIST = TypeAdapter(list[DocumentSpec])


def load_source_catalog(path: Path) -> list[DocumentSpec]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(payload, dict):
        payload = payload.get("documents", [])
    documents = _DOCUMENT_LIST.validate_python(payload)
    ids = [item.document_id for item in documents]
    if len(ids) != len(set(ids)):
        raise ValueError("Catálogo Knowledge contém document_id duplicado")
    return documents
