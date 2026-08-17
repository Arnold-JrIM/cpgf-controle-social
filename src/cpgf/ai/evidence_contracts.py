from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Literal, TypeAlias

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from cpgf.ai.contracts import ToolName
from cpgf.ai.router import Route
from cpgf.knowledge.models import (
    AuthorityLevel,
    CorpusScope,
    SourceClass,
    TemporalStatus,
)

EVIDENCE_CONTRACT_VERSION = "1.0.0"

JsonScalar: TypeAlias = str | int | float | bool | None
ParameterValue: TypeAlias = JsonScalar | tuple[JsonScalar, ...]
_ALLOWED_TRAILS = frozenset(f"T{number:02d}" for number in range(1, 10))


class EvidenceSource(StrEnum):
    """Camadas de evidência autorizadas pelo Orchestrator 2.0."""

    DATA = "data"
    KNOWLEDGE = "knowledge"
    WEB = "web"


class StrictEvidenceModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class EvidenceParameter(StrictEvidenceModel):
    """Parâmetro auditável sem dicionário mutável na fronteira entre componentes."""

    name: str = Field(pattern=r"^[a-z][a-z0-9_]{1,63}$")
    value: ParameterValue


class EvidenceVersion(StrictEvidenceModel):
    """Versão de um artefato que participou da produção da evidência."""

    component: str = Field(pattern=r"^[a-z][a-z0-9_.-]{1,63}$")
    version: str = Field(min_length=1, max_length=100)


class EvidenceNeed(StrictEvidenceModel):
    """Uma necessidade de evidência declarada pelo Orchestrator."""

    need_id: str = Field(pattern=r"^need-[a-z0-9][a-z0-9_-]{1,63}$")
    source: EvidenceSource
    objective: str = Field(min_length=3, max_length=600)
    required: bool = True
    freshness_required: bool = False
    query_hint: str | None = Field(default=None, min_length=3, max_length=600)
    scopes: tuple[CorpusScope, ...] = Field(default=(), max_length=6)
    temporal_statuses: tuple[TemporalStatus, ...] = Field(default=(), max_length=3)
    source_classes: tuple[SourceClass, ...] = Field(default=(), max_length=7)
    trail_hints: tuple[str, ...] = Field(default=(), max_length=9)
    tool_hints: tuple[ToolName, ...] = Field(default=(), max_length=7)
    parameters: tuple[EvidenceParameter, ...] = Field(default=(), max_length=30)

    @field_validator("scopes", "temporal_statuses", "source_classes", "tool_hints")
    @classmethod
    def deduplicate_enums(cls, values: tuple[object, ...]) -> tuple[object, ...]:
        return tuple(dict.fromkeys(values))

    @field_validator("trail_hints", mode="before")
    @classmethod
    def normalize_trails(cls, value: object) -> tuple[str, ...]:
        if value in (None, ""):
            return ()
        raw = value if isinstance(value, (list, tuple, set)) else (value,)
        normalized = tuple(dict.fromkeys(str(item).strip().upper() for item in raw))
        invalid = sorted(set(normalized) - _ALLOWED_TRAILS)
        if invalid:
            raise ValueError(f"Trilhas inválidas: {invalid}")
        return normalized

    @model_validator(mode="after")
    def validate_source_contract(self) -> "EvidenceNeed":
        parameter_names = [parameter.name for parameter in self.parameters]
        if len(parameter_names) != len(set(parameter_names)):
            raise ValueError("parameters não pode repetir nomes")

        if self.source is not EvidenceSource.DATA and self.tool_hints:
            raise ValueError("tool_hints é permitido somente para evidência DATA")

        if self.source is EvidenceSource.DATA and (
            self.scopes or self.temporal_statuses or self.source_classes
        ):
            raise ValueError(
                "filtros documentais scopes/temporal_statuses/source_classes não pertencem a DATA"
            )

        if self.source is EvidenceSource.WEB and self.scopes:
            raise ValueError("scopes do corpus governado não pertencem a WEB")

        return self


class EvidencePlan(StrictEvidenceModel):
    """Plano multi-rótulo; declara necessidades, mas não executa ferramentas."""

    contract_version: Literal["1.0.0"] = EVIDENCE_CONTRACT_VERSION
    question: str = Field(min_length=3, max_length=4000)
    needs: tuple[EvidenceNeed, ...] = Field(default=(), max_length=3)
    reason: str = Field(min_length=3, max_length=1000)
    legacy_route: Route | None = None

    @model_validator(mode="after")
    def validate_unique_needs(self) -> "EvidencePlan":
        need_ids = [need.need_id for need in self.needs]
        if len(need_ids) != len(set(need_ids)):
            raise ValueError("need_id deve ser único dentro do EvidencePlan")

        sources = [need.source for need in self.needs]
        if len(sources) != len(set(sources)):
            raise ValueError(
                "EvidencePlan 1.0 aceita no máximo uma necessidade agregada por fonte"
            )
        return self

    @property
    def required_sources(self) -> tuple[EvidenceSource, ...]:
        return tuple(need.source for need in self.needs if need.required)

    @property
    def requested_sources(self) -> tuple[EvidenceSource, ...]:
        return tuple(need.source for need in self.needs)

    def need_for(self, source: EvidenceSource) -> EvidenceNeed | None:
        return next((need for need in self.needs if need.source is source), None)


class EvidenceItem(StrictEvidenceModel):
    """Unidade de evidência inspecionável produzida por um worker especializado."""

    evidence_id: str = Field(pattern=r"^ev-[a-z0-9][a-z0-9_-]{1,79}$")
    need_id: str = Field(pattern=r"^need-[a-z0-9][a-z0-9_-]{1,63}$")
    source: EvidenceSource
    content: str = Field(min_length=1, max_length=20000)
    citation: str = Field(min_length=1, max_length=2000)
    source_ref: str = Field(min_length=1, max_length=1000)

    tool: ToolName | None = None
    parameters: tuple[EvidenceParameter, ...] = Field(default=(), max_length=50)
    versions: tuple[EvidenceVersion, ...] = Field(default=(), max_length=20)

    document_id: str | None = Field(default=None, min_length=3, max_length=120)
    chunk_id: str | None = Field(default=None, min_length=1, max_length=200)
    page: int | None = Field(default=None, ge=1)
    section: str | None = Field(default=None, max_length=500)
    source_class: SourceClass | None = None
    authority_level: AuthorityLevel | None = None
    scope: CorpusScope | None = None
    temporal_status: TemporalStatus | None = None
    retrieval_score: float | None = Field(default=None, ge=0)
    retrieval_method: Literal["lexical", "semantic", "hybrid", "tool", "web"] | None = None

    source_url: str | None = Field(default=None, min_length=5, max_length=4000)
    observed_at: datetime | None = None

    @model_validator(mode="after")
    def validate_provenance(self) -> "EvidenceItem":
        parameter_names = [parameter.name for parameter in self.parameters]
        if len(parameter_names) != len(set(parameter_names)):
            raise ValueError("parameters não pode repetir nomes")

        version_components = [version.component for version in self.versions]
        if len(version_components) != len(set(version_components)):
            raise ValueError("versions não pode repetir componentes")

        if self.source is EvidenceSource.DATA:
            if self.tool is None:
                raise ValueError("evidência DATA exige tool registrado")
            if self.retrieval_method not in (None, "tool"):
                raise ValueError("evidência DATA usa retrieval_method='tool' quando informado")

        if self.source is EvidenceSource.KNOWLEDGE:
            if self.tool is not None:
                raise ValueError("evidência KNOWLEDGE não pode declarar tool de Serving")
            if self.document_id is None:
                raise ValueError("evidência KNOWLEDGE exige document_id")
            if self.retrieval_method not in (None, "lexical", "semantic", "hybrid"):
                raise ValueError("retrieval_method inválido para KNOWLEDGE")

        if self.source is EvidenceSource.WEB:
            if self.tool is not None:
                raise ValueError("evidência WEB não pode declarar tool de Serving")
            if self.source_url is None or self.observed_at is None:
                raise ValueError("evidência WEB exige source_url e observed_at")
            if self.retrieval_method not in (None, "web"):
                raise ValueError("evidência WEB usa retrieval_method='web' quando informado")

        return self


class EvidenceBundle(StrictEvidenceModel):
    """Pacote governado entregue ao futuro Synthesizer/Verifier."""

    contract_version: Literal["1.0.0"] = EVIDENCE_CONTRACT_VERSION
    plan: EvidencePlan
    items: tuple[EvidenceItem, ...] = ()
    warnings: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_bundle_alignment(self) -> "EvidenceBundle":
        evidence_ids = [item.evidence_id for item in self.items]
        if len(evidence_ids) != len(set(evidence_ids)):
            raise ValueError("evidence_id deve ser único dentro do EvidenceBundle")

        needs = {need.need_id: need for need in self.plan.needs}
        for item in self.items:
            need = needs.get(item.need_id)
            if need is None:
                raise ValueError(
                    f"evidência {item.evidence_id} referencia need_id não planejado: {item.need_id}"
                )
            if item.source is not need.source:
                raise ValueError(
                    f"evidência {item.evidence_id} usa fonte {item.source.value} incompatível "
                    f"com {item.need_id} ({need.source.value})"
                )
        return self

    @property
    def satisfied_need_ids(self) -> tuple[str, ...]:
        present = {item.need_id for item in self.items}
        return tuple(need.need_id for need in self.plan.needs if need.need_id in present)

    @property
    def missing_required_need_ids(self) -> tuple[str, ...]:
        present = {item.need_id for item in self.items}
        return tuple(
            need.need_id
            for need in self.plan.needs
            if need.required and need.need_id not in present
        )

    @property
    def is_complete(self) -> bool:
        return not self.missing_required_need_ids

    def items_for(self, source: EvidenceSource) -> tuple[EvidenceItem, ...]:
        return tuple(item for item in self.items if item.source is source)
