from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import pandas as pd

from cpgf.ingestion.validators import CPGF_REFERENCE_COLUMNS

RAW_REQUIRED_COLUMNS = tuple(CPGF_REFERENCE_COLUMNS)
OPTIONAL_PROVENANCE_COLUMNS = ("COMPETENCIA_ARQUIVO", "ARQUIVO_ORIGEM")


class SchemaError(ValueError):
    """Schema de entrada incompatível com o contrato CPGF."""


@dataclass(frozen=True)
class SchemaInspection:
    missing_required: tuple[str, ...]
    extra_columns: tuple[str, ...]

    @property
    def valid(self) -> bool:
        return not self.missing_required


def inspect_columns(columns: Iterable[str]) -> SchemaInspection:
    observed = tuple(str(column) for column in columns)
    observed_set = set(observed)
    required_set = set(RAW_REQUIRED_COLUMNS)
    missing = tuple(column for column in RAW_REQUIRED_COLUMNS if column not in observed_set)
    extra = tuple(column for column in observed if column not in required_set)
    return SchemaInspection(missing_required=missing, extra_columns=extra)


def validate_raw_frame(frame: pd.DataFrame) -> SchemaInspection:
    inspection = inspect_columns(frame.columns)
    if not inspection.valid:
        missing = ", ".join(inspection.missing_required)
        raise SchemaError(f"Colunas obrigatórias ausentes: {missing}")
    return inspection
