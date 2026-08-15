from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class SourceClass(StrEnum):
    NORMATIVE = "normative"
    INSTITUTIONAL = "institutional"
    SCIENTIFIC = "scientific"
    ACADEMIC = "academic"
    PROJECT = "project"
    WEB = "web"


class AuthorityLevel(StrEnum):
    PRIMARY_NORMATIVE = "primary_normative"
    OFFICIAL_INSTITUTIONAL = "official_institutional"
    SCIENTIFIC_PEER_REVIEWED = "scientific_peer_reviewed"
    SCIENTIFIC_CONFERENCE = "scientific_conference"
    ACADEMIC_THESIS = "academic_thesis"
    PROJECT_CONTROLLED = "project_controlled"
    WEB_UNCLASSIFIED = "web_unclassified"


class DistributionPolicy(StrEnum):
    PUBLIC_OFFICIAL = "public_official"
    OPEN_LICENSE = "open_license"
    METADATA_ONLY = "metadata_only"
    PROJECT_OWNED = "project_owned"


class DocumentSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    document_id: str = Field(pattern=r"^[a-z0-9][a-z0-9_-]{2,80}$")
    title: str = Field(min_length=3, max_length=500)
    source_class: SourceClass
    authority_level: AuthorityLevel
    distribution_policy: DistributionPolicy
    expected_filename: str | None = None
    authors: list[str] = Field(default_factory=list)
    authority: str | None = None
    year: int | None = Field(default=None, ge=1900, le=2100)
    publisher: str | None = None
    citation: str
    doi: str | None = None
    source_url: str | None = None
    license_name: str | None = None
    trails: list[str] = Field(default_factory=list)
    active: bool = True
    notes: str | None = None

    @field_validator("expected_filename")
    @classmethod
    def validate_filename(cls, value: str | None) -> str | None:
        if value is None:
            return value
        if value.startswith(("/", "\\")) or ".." in value.replace("\\", "/").split("/"):
            raise ValueError("expected_filename deve permanecer dentro de source_root")
        if "/" in value or "\\" in value:
            raise ValueError("expected_filename deve conter apenas o nome do arquivo")
        return value

    @field_validator("trails")
    @classmethod
    def validate_trails(cls, values: list[str]) -> list[str]:
        allowed = {f"T{number:02d}" for number in range(1, 10)}
        invalid = sorted(set(values) - allowed)
        if invalid:
            raise ValueError(f"Trilhas inválidas: {invalid}")
        return sorted(set(values))


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
    source_url: str | None = None
    retrieval_method: Literal["lexical"] = "lexical"
