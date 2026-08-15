from __future__ import annotations

import hashlib
import re
from pathlib import Path

from pypdf import PdfReader

from .models import LoadedSection

_WHITESPACE = re.compile(r"[ \t]+")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalize_text(text: str) -> str:
    lines = [_WHITESPACE.sub(" ", line).strip() for line in text.replace("\r", "\n").split("\n")]
    output: list[str] = []
    blank = False
    for line in lines:
        if line:
            output.append(line)
            blank = False
        elif output and not blank:
            output.append("")
            blank = True
    return "\n".join(output).strip()


def load_document(path: Path, document_id: str) -> list[LoadedSection]:
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        reader = PdfReader(str(path))
        sections = []
        for index, page in enumerate(reader.pages, start=1):
            text = normalize_text(page.extract_text() or "")
            if text:
                sections.append(LoadedSection(document_id=document_id, text=text, page=index))
        return sections
    if suffix in {".md", ".txt"}:
        text = normalize_text(path.read_text(encoding="utf-8"))
        return [LoadedSection(document_id=document_id, text=text)] if text else []
    raise ValueError(f"Formato documental não suportado no Knowledge 1.0.0: {suffix}")
