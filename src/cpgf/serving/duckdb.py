from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import duckdb

_LOGICAL_NAME_RE = re.compile(r"^[a-z][a-z0-9_]*$")


def validate_logical_name(name: str) -> str:
    """Restringe nomes lógicos usados como identificadores SQL."""
    normalized = str(name).strip().lower()
    if not _LOGICAL_NAME_RE.fullmatch(normalized):
        raise ValueError(f"Nome lógico inválido para serving: {name!r}")
    return normalized


def _sql_literal(value: str) -> str:
    return "'" + str(value).replace("'", "''") + "'"


def _sql_identifier(value: str) -> str:
    return '"' + str(value).replace('"', '""') + '"'


def build_duckdb_catalog(
    bundle_dir: Path,
    manifest_path: Path,
    catalog_path: Path,
) -> Path:
    """Cria catálogo DuckDB autocontido a partir dos Parquets do bundle."""
    bundle_dir = Path(bundle_dir)
    manifest_path = Path(manifest_path)
    catalog_path = Path(catalog_path)
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    tables = payload.get("tables", [])
    if not isinstance(tables, list) or not tables:
        raise ValueError("Manifesto de serving sem tabelas materializadas.")

    catalog_path.parent.mkdir(parents=True, exist_ok=True)
    if catalog_path.exists():
        catalog_path.unlink()

    connection = duckdb.connect(str(catalog_path))
    try:
        connection.execute(
            """
            CREATE TABLE serving_catalog (
                logical_name VARCHAR PRIMARY KEY,
                table_name VARCHAR NOT NULL,
                view_name VARCHAR NOT NULL,
                parquet_path VARCHAR NOT NULL,
                kind VARCHAR NOT NULL,
                row_count BIGINT NOT NULL,
                sha256 VARCHAR NOT NULL
            )
            """
        )
        for item in tables:
            if not isinstance(item, dict):
                raise TypeError("Entrada inválida em tables do manifesto de serving.")
            name = validate_logical_name(str(item["name"]))
            table_name = f"srv_{name}"
            view_name = f"v_{name}"
            parquet_path = bundle_dir / str(item["path"])
            if not parquet_path.is_file():
                raise FileNotFoundError(f"Parquet ausente: {parquet_path}")

            connection.execute(
                f"CREATE TABLE {_sql_identifier(table_name)} AS "
                f"SELECT * FROM read_parquet({_sql_literal(str(parquet_path))})"
            )
            connection.execute(
                f"CREATE VIEW {_sql_identifier(view_name)} AS "
                f"SELECT * FROM {_sql_identifier(table_name)}"
            )
            actual_rows = int(
                connection.execute(
                    f"SELECT COUNT(*) FROM {_sql_identifier(table_name)}"
                ).fetchone()[0]
            )
            expected_rows = int(item["rows"])
            if actual_rows != expected_rows:
                raise ValueError(
                    f"Cardinalidade divergente em {name}: "
                    f"manifesto={expected_rows}, DuckDB={actual_rows}."
                )
            connection.execute(
                "INSERT INTO serving_catalog VALUES (?, ?, ?, ?, ?, ?, ?)",
                [
                    name,
                    table_name,
                    view_name,
                    str(item["path"]),
                    str(item["kind"]),
                    expected_rows,
                    str(item["sha256"]),
                ],
            )
        connection.execute("CHECKPOINT")
    finally:
        connection.close()
    return catalog_path


def open_catalog(path: Path, *, read_only: bool = True) -> duckdb.DuckDBPyConnection:
    """Abre o catálogo de serving, por padrão somente para leitura."""
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"Catálogo DuckDB inexistente: {path}")
    return duckdb.connect(str(path), read_only=read_only)


def catalog_metadata(path: Path) -> list[dict[str, Any]]:
    """Retorna o catálogo lógico sem expor SQL arbitrário."""
    connection = open_catalog(path)
    try:
        frame = connection.execute(
            """
            SELECT logical_name, table_name, view_name, parquet_path, kind, row_count, sha256
            FROM serving_catalog
            ORDER BY logical_name
            """
        ).df()
    finally:
        connection.close()
    return frame.to_dict(orient="records")
