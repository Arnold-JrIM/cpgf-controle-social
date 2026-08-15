from __future__ import annotations

from enum import StrEnum
from pathlib import PurePosixPath
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class SourceClass(StrEnum):
    NORMATIVE = "normative"
    INSTITUTIONAL = "institutional"
    CONTROL_EXTERNAL = "control_external"
    SCIENTIFIC = "scientific"
    ACADEMIC = "academic"
    PROJECT = "project"
    WEB = "web"


class AuthorityLevel(StrEnum):
    PRIMARY_NORMATIVE = "primary_normative"
    OFFICIAL_INSTITUTIONAL = "official_institutional"
    OFFICIAL_CONTROL_DECISION = "official_control_decision"
    SCIENTIFIC_PEER_REVIEWED = "scientific_peer_reviewed"
    SCIENTIFIC_CONFERENCE = "scientific_conference"
    SCHOLARLY_BOOK = "scholarly_book"
    ACADEMIC_THESIS = "academic_thesis"
    ACADEMIC_WORK = "academic_work"
    PROJECT_CONTROLLED = "project_controlled"
    WEB_UNCLASSIFIED = "web_unclassified"


class DistributionPolicy(StrEnum):
    PUBLIC_OFFICIAL = "public_official"
    OPEN_LICENSE = "open_license"
    METADATA_ONLY = "metadata_only"
    PROJECT_OWNED = "project_owned"


class CorpusScope(StrEnum):
    CPGF_CORE = "cpgf_core"
    METHODOLOGY = "methodology"
    CONTROL_EXTERNAL = "control_external"
    HISTORICAL = "historical"
    INSTITUTIONAL_MB = "institutional_mb"
    DISCOVERY = "discovery"


class TemporalStatus(StrEnum):
    CURRENT = "current"
    HISTORICAL = "historical"
    CONTEXTUAL = "contextual"


def _validate_relative_path(value: str | None, *, allow_directories: bool) -> str | None:
    if value is None:
        return value
    normalized = value.replace("\\", "/").strip()
    path = PurePosixPath(normalized)
    if not normalized or path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise ValueError("caminho documental deve ser relativo e permanecer dentro de source_root")
    if not allow_directories and len(path.parts) != 1:
        raise ValueError("expected_filename deve conter apenas o nome do arquivo")
    return normalized


class DocumentSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    document_id: str = Field(pattern=r"^[a-z0-9][a-z0-9_-]{2,80}$")
    title: str = Field(min_length=3, max_length=500)
    source_class: SourceClass
    authority_level: AuthorityLevel
    distribution_policy: DistributionPolicy
    expected_filename: str | None = None
    expected_path: str | None = None
    expected_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    expected_bytes: int | None = Field(default=None, ge=0)
    expected_pages: int | None = Field(default=None, ge=1)
    authors: list[str] = Field(default_factory=list)
    authority: str | None = None
    year: int | None = Field(default=None, ge=1900, le=2100)
    publisher: str | None = None
    citation: str
    doi: str | None = None
    source_url: str | None = None
    license_name: str | None = None
    scope: CorpusScope = CorpusScope.CPGF_CORE
    temporal_status: TemporalStatus = TemporalStatus.CURRENT
    retrieval_default: bool = True
    ingest_content: bool = True
    supports_trails: list[str] = Field(default_factory=list)
    related_trails: list[str] = Field(default_factory=list)
    trails: list[str] = Field(default_factory=list)
    active: bool = True
    notes: str | None = None

    @field_validator("expected_filename")
    @classmethod
    def validate_filename(cls, value: str | None) -> str | None:
        return _validate_relative_path(value, allow_directories=False)

    @field_validator("expected_path")
    @classmethod
    def validate_expected_path(cls, value: str | None) -> str | None:
        return _validate_relative_path(value, allow_directories=True)

    @field_validator("supports_trails", "related_trails", "trails")
    @classmethod
    def validate_trails(cls, values: list[str]) -> list[str]:
        allowed = {f"T{number:02d}" for number in range(1, 10)}
        invalid = sorted(set(values) - allowed)
        if invalid:
            raise ValueError(f"Trilhas inválidas: {invalid}")
        return sorted(set(values))

    @property
    def source_relative_path(self) -> str | None:
        return self.expected_path or self.expected_filename


class LoadedSection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    document_id: str
    text: str
    page: int | None = None
    section: str | None = None


class KnowledgeChunk(BaseModel):
    model_config = ConfigDict(extra="forbid")

    chunk_id: str
    document_id: str
    text: str
    ordinal: int = Field(ge=0)
    page: int | None = Field(default=None, ge=1)
    section: str | None = None
    source_class: SourceClass
    authority_level: AuthorityLevel
    scope: CorpusScope
    temporal_status: TemporalStatus
    retrieval_default: bool
    supports_trails: list[str] = Field(default_factory=list)
    related_trails: list[str] = Field(default_factory=list)
    citation: str
    source_url: str | None = None
    source_sha256: str | None = None


class SearchHit(BaseModel):
    model_config = ConfigDict(extra="forbid")

    chunk_id: str
    document_id: str
    score: float = Field(ge=0)
    text: str
    page: int | None = None
    citation: str
    source_class: SourceClass
    authority_level: AuthorityLevel
    scope: CorpusScope
    temporal_status: TemporalStatus
    retrieval_default: bool
    source_url: str | None = None
    retrieval_method: Literal["lexical", "semantic", "hybrid"] = "lexical"
