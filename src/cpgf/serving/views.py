from __future__ import annotations

import json
from pathlib import Path


def authorized_views_from_manifest(manifest_path: Path) -> dict[str, str]:
    """Mapeia nome lógico para a view DuckDB autorizada."""
    payload = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    tables = payload.get("tables", [])
    if not isinstance(tables, list):
        raise TypeError("Manifesto de serving inválido em tables.")
    result: dict[str, str] = {}
    for item in tables:
        if not isinstance(item, dict):
            raise TypeError("Entrada inválida no manifesto de serving.")
        name = str(item["name"])
        result[name] = f"v_{name}"
    return dict(sorted(result.items()))
