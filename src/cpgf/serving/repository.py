from __future__ import annotations

from pathlib import Path

import pandas as pd

from .duckdb import open_catalog, validate_logical_name


class ServingRepository:
    """Camada de leitura limitada às views autorizadas do catálogo de serving."""

    def __init__(self, catalog_path: Path):
        self.catalog_path = Path(catalog_path)

    def list_views(self) -> list[str]:
        connection = open_catalog(self.catalog_path)
        try:
            rows = connection.execute(
                "SELECT view_name FROM serving_catalog ORDER BY logical_name"
            ).fetchall()
        finally:
            connection.close()
        return [str(row[0]) for row in rows]

    def read(
        self,
        logical_name: str,
        *,
        limit: int = 1_000,
        offset: int = 0,
    ) -> pd.DataFrame:
        name = validate_logical_name(logical_name)
        limit = int(limit)
        offset = int(offset)
        if limit < 1 or limit > 100_000:
            raise ValueError("limit deve estar entre 1 e 100.000.")
        if offset < 0:
            raise ValueError("offset não pode ser negativo.")

        connection = open_catalog(self.catalog_path)
        try:
            exists = connection.execute(
                "SELECT 1 FROM serving_catalog WHERE logical_name = ?",
                [name],
            ).fetchone()
            if exists is None:
                raise KeyError(f"Tabela lógica não autorizada: {name}")
            view_name = f"v_{name}"
            return connection.execute(
                f'SELECT * FROM "{view_name}" LIMIT {limit} OFFSET {offset}'
            ).df()
        finally:
            connection.close()

    def count(self, logical_name: str) -> int:
        name = validate_logical_name(logical_name)
        connection = open_catalog(self.catalog_path)
        try:
            row = connection.execute(
                "SELECT row_count FROM serving_catalog WHERE logical_name = ?",
                [name],
            ).fetchone()
            if row is None:
                raise KeyError(f"Tabela lógica não autorizada: {name}")
            return int(row[0])
        finally:
            connection.close()
