from __future__ import annotations

import re
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator

from cpgf.ai.contracts import ToolName
from cpgf.knowledge.models import CorpusScope, TemporalStatus
from cpgf.version import BENCHMARK_VERSION

_CASE_ID = re.compile(r"^BENCH-\d{3}$")
_TRAILS = {f"T{i:02d}" for i in range(1, 10)}


class QuestionFamily(StrEnum):
    CONCEPTUAL_NORMATIVE = "conceptual_normative"
    SERVING_QUERY = "serving_query"
    TRAIL_QUERY = "trail_query"
    MOTOR_RULE = "motor_rule"
    SAFETY_INTERPRETATION = "safety_interpretation"


class ExpectedRoute(StrEnum):
    KNOWLEDGE = "knowledge"
    OVERVIEW = "overview"
    TRAILS = "trails"
    TERRITORIAL = "territorial"
    SUPPLIERS = "suppliers"
    UGS = "ugs"
    METHODOLOGY = "methodology"
    COMPOSITE = "composite"


class BenchmarkCase(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    question: str = Field(min_length=5, max_length=500)
    family: QuestionFamily
    expected_route: ExpectedRoute
    expected_tools: tuple[ToolName, ...] = ()
    gold_document_ids: tuple[str, ...] = ()
    supporting_document_ids: tuple[str, ...] = ()
    expected_scopes: tuple[CorpusScope, ...] = ()
    expected_temporal_statuses: tuple[TemporalStatus, ...] = ()
    expected_trails: tuple[str, ...] = ()
    expected_concepts: tuple[str, ...] = ()
    forbidden_claims: tuple[str, ...] = ()
    requires_serving: bool = False
    requires_knowledge: bool = False
    freshness_sensitive: bool = False
    notes: str | None = None

    @model_validator(mode="after")
    def validate_contract(self) -> "BenchmarkCase":
        if not _CASE_ID.fullmatch(self.id):
            raise ValueError(f"ID inválido: {self.id}")
        invalid_trails = sorted(set(self.expected_trails) - _TRAILS)
        if invalid_trails:
            raise ValueError(f"Trilhas inválidas: {invalid_trails}")
        if self.family is QuestionFamily.SERVING_QUERY and not self.requires_serving:
            raise ValueError("serving_query requer requires_serving=true")
        if self.family is QuestionFamily.SERVING_QUERY and not self.expected_tools:
            raise ValueError("serving_query requer ao menos uma ferramenta esperada")
        if self.family is QuestionFamily.SAFETY_INTERPRETATION and not self.forbidden_claims:
            raise ValueError("safety_interpretation requer afirmações proibidas")
        if self.expected_route is ExpectedRoute.KNOWLEDGE and not self.requires_knowledge:
            raise ValueError("rota knowledge requer requires_knowledge=true")
        if self.gold_document_ids and not self.requires_knowledge:
            raise ValueError("gold_document_ids requer requires_knowledge=true")
        return self


class BenchmarkSuite(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    benchmark_version: str = BENCHMARK_VERSION
    title: str = "Benchmark de Recuperação e Roteamento do Assistente CPGF"
    cases: tuple[BenchmarkCase, ...]

    @model_validator(mode="after")
    def validate_suite(self) -> "BenchmarkSuite":
        if self.benchmark_version != BENCHMARK_VERSION:
            raise ValueError(f"Versão do benchmark deve ser {BENCHMARK_VERSION}")
        if not 40 <= len(self.cases) <= 100:
            raise ValueError("Benchmark deve conter entre 40 e 100 casos")
        ids = [case.id for case in self.cases]
        if len(ids) != len(set(ids)):
            raise ValueError("IDs duplicados no benchmark")
        covered = {trail for case in self.cases for trail in case.expected_trails}
        if covered != _TRAILS:
            missing = sorted(_TRAILS - covered)
            raise ValueError(f"Benchmark não cobre todas as trilhas: {missing}")
        families = {case.family for case in self.cases}
        if families != set(QuestionFamily):
            raise ValueError("Benchmark deve cobrir todas as famílias de perguntas")
        return self
