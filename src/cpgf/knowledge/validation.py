from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from .loader import sha256_file


def validate_knowledge_bundle(bundle_dir: Path) -> dict[str, object]:
    bundle_dir = Path(bundle_dir)
    manifest_path = bundle_dir / "knowledge_manifest.json"
    if not manifest_path.is_file():
        return {"status": "FAIL", "reason": "manifest_missing"}
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    checks: list[dict[str, object]] = []
    for filename in ("documents.parquet", "chunks.parquet"):
        path = bundle_dir / filename
        expected = manifest.get("artifacts", {}).get(filename, {}).get("sha256")
        passed = path.is_file() and expected == sha256_file(path)
        checks.append({"artifact": filename, "pass": passed})
    if not all(item["pass"] for item in checks):
        return {"status": "FAIL", "artifact_checks": checks}

    documents = pd.read_parquet(bundle_dir / "documents.parquet")
    chunks = pd.read_parquet(bundle_dir / "chunks.parquet")
    document_ids = set(documents["document_id"].astype(str)) if not documents.empty else set()
    orphan_chunks = []
    if not chunks.empty:
        orphan_chunks = sorted(set(chunks["document_id"].astype(str)) - document_ids)
    duplicate_chunks = bool(chunks["chunk_id"].duplicated().any()) if not chunks.empty else False
    status = "PASS" if not orphan_chunks and not duplicate_chunks else "FAIL"
    return {
        "status": status,
        "artifact_checks": checks,
        "documents": int(len(documents)),
        "chunks": int(len(chunks)),
        "orphan_chunks": orphan_chunks,
        "duplicate_chunks": duplicate_chunks,
    }
