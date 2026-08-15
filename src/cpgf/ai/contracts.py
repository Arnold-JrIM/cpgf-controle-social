from __future__ import annotations

import json
import re
from enum import StrEnum
from typing import Any, Literal

import pandas as pd
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from cpgf.geography.ug_dimension import UFS_BRASIL

_UG_RE = re.compile(r"^\d{6}$")
_METRIC_RE = re.compile(r"^[A-Z][A-Z0-9_]*$")


class ToolName(StrEnum):
    OVERVIEW = "overview"
    TRAIL_PREVALENCE = "trail_prevalence"
    TOP_UGS = "top_ugs"
    TOP_SUPPLIERS = "top_suppliers"
    TERRITORIAL_METRIC = "territorial_metric"
    TERRITORIAL_UG_CONTEXT = "territorial_ug_context"
    METHODOLOGY = "methodology"


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class QueryScope(StrictModel):
    year_start: int = Field(ge=2013, le=2100)
    year_end: int = Field(ge=2013, le=2100)
    ug_codes: tuple[str, ...] = Field(default=(), max_length=100)

    @model_validator(mode="after")
    def validate_year_order(self) -> "QueryScope":
        if self.year_start > self.year_end:
            raise ValueError("year_start não pode ser posterior a year_end.")
        return self

    @field_validator("ug_codes", mode="before")
    @classmethod
    def normalize_ugs(cls, value: object) -> tuple[str, ...]:
        if value in (None, ""):
            return ()
        values = value if isinstance(value, (list, tuple, set)) else (value,)
        normalized = tuple(dict.fromkeys(str(item).strip() for item in values))
        invalid = [item for item in normalized if not _UG_RE.fullmatch(item)]
        if invalid:
            raise ValueError(f"UG deve conter exatamente seis dígitos: {invalid[:3]}.")
        return normalized


class RankingArgs(QueryScope):
    limit: int = Field(default=20, ge=1, le=100)


class TerritorialMetricArgs(StrictModel):
    reference: Literal["TRANSACAO", "EXTRATO"]
    year: int = Field(ge=2013, le=2100)
    metric: str

    @field_validator("metric")
    @classmethod
    def normalize_metric(cls, value: str) -> str:
        metric = str(value).strip().upper()
        if not _METRIC_RE.fullmatch(metric):
            raise ValueError("Métrica territorial fora do formato autorizado.")
        return metric


class TerritorialUGArgs(StrictModel):
    uf: str
    year: int = Field(ge=2013, le=2100)
    limit: int = Field(default=25, ge=1, le=100)

    @field_validator("uf")
    @classmethod
    def validate_uf(cls, value: str) -> str:
        uf = str(value).strip().upper()
        if uf not in UFS_BRASIL:
            raise ValueError(f"UF inválida: {value}.")
        return uf


class EmptyArgs(StrictModel):
    pass


class ToolRequest(StrictModel):
    tool: ToolName
    arguments: dict[str, Any] = Field(default_factory=dict)


class ToolProvenance(StrictModel):
    serving_version: str
    rules_version: str
    motor_version: str
    geo_version: str
    read_only: bool = True
    source: str = "serving_views"


class ToolResult(StrictModel):
    tool: ToolName
    records: list[dict[str, Any]] = Field(default_factory=list)
    summary: dict[str, Any] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    provenance: ToolProvenance


def dataframe_records(frame: pd.DataFrame) -> list[dict[str, Any]]:
    """Converte DataFrame em registros JSON-safe para a fronteira do agente."""
    if frame.empty:
        return []
    return json.loads(frame.to_json(orient="records", date_format="iso"))
