from __future__ import annotations

import csv
import gzip
import hashlib
import json
import re
import unicodedata
from collections import Counter
from difflib import SequenceMatcher
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from cpgf.ai.contracts import ToolName
from cpgf.ai.evidence_contracts import EvidenceParameter, EvidenceSource
from cpgf.ai.evidence_workers import DATA_EVIDENCE_TOOLS
from cpgf.ai.tools.registry import TOOL_REGISTRY
from cpgf.ai.web_evidence import WebQueryOptions
from cpgf.knowledge.models import CorpusScope, SourceClass, TemporalStatus

ORCHESTRATION_HOLDOUT_V2_VERSION = "2.0.0"

_CASE_ID = re.compile(r"^OH2-\d{3}$")
_CATEGORY_SOURCES = {
    "data_only": (EvidenceSource.DATA,),
    "knowledge_only": (EvidenceSource.KNOWLEDGE,),
    "web_only": (EvidenceSource.WEB,),
    "data_knowledge": (EvidenceSource.DATA, EvidenceSource.KNOWLEDGE),
    "knowledge_web": (EvidenceSource.KNOWLEDGE, EvidenceSource.WEB),
    "data_web": (EvidenceSource.DATA, EvidenceSource.WEB),
    "all_three": (
        EvidenceSource.DATA,
        EvidenceSource.KNOWLEDGE,
        EvidenceSource.WEB,
    ),
}

# Universo de novidade congelado junto com o OH2. Não deve crescer retroativamente.
FROZEN_PRIOR_BENCHMARK_PATHS = (
    Path("data/benchmarks/assistant_router_holdout_v1_0_0.csv"),
    Path("data/benchmarks/assistant_router_holdout_v2_0_0.csv"),
    Path("data/benchmarks/assistant_v1_0_0.csv"),
    Path("data/benchmarks/joint_retrieval_holdout_v2_0_0.csv"),
    Path("data/benchmarks/joint_retrieval_holdout_v3_0_0.csv"),
    Path("data/benchmarks/joint_retrieval_holdout_v4_0_0.csv"),
    Path("data/benchmarks/joint_retrieval_holdout_v5_0_0.csv"),
    Path("data/benchmarks/knowledge_retrieval_v1_0_0.csv"),
    Path("data/benchmarks/orchestration_holdout_v1_0_0.csv.gz"),
    Path("data/benchmarks/retrieval_planner_holdout_v1_0_0.csv"),
)


class OrchestrationHoldoutV2Category(StrEnum):
    DATA_ONLY = "data_only"
    KNOWLEDGE_ONLY = "knowledge_only"
    WEB_ONLY = "web_only"
    DATA_KNOWLEDGE = "data_knowledge"
    KNOWLEDGE_WEB = "knowledge_web"
    DATA_WEB = "data_web"
    ALL_THREE = "all_three"


class OrchestrationHoldoutV2Case(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    category: OrchestrationHoldoutV2Category
    question: str = Field(min_length=10, max_length=600)
    expected_status: str = Field(pattern=r"^planned$")
    expected_sources: tuple[EvidenceSource, ...]
    expected_data_tool: ToolName | None = None
    expected_data_parameters: tuple[EvidenceParameter, ...] = ()
    expected_knowledge_scopes: tuple[CorpusScope, ...] = ()
    expected_knowledge_temporal_statuses: tuple[TemporalStatus, ...] = ()
    expected_knowledge_source_classes: tuple[SourceClass, ...] = ()
    expected_web_parameters: tuple[EvidenceParameter, ...] = ()
    notes: str | None = None

    @model_validator(mode="after")
    def validate_contract(self) -> "OrchestrationHoldoutV2Case":
        if not _CASE_ID.fullmatch(self.id):
            raise ValueError(f"ID inválido: {self.id}")

        expected_by_category = _CATEGORY_SOURCES[self.category.value]
        if self.expected_sources != expected_by_category:
            raise ValueError(
                f"{self.id} fontes incompatíveis com {self.category.value}: "
                f"{self.expected_sources}"
            )

        if EvidenceSource.DATA in self.expected_sources:
            if self.expected_data_tool is None:
                raise ValueError(f"{self.id} exige ferramenta DATA")
            if self.expected_data_tool not in DATA_EVIDENCE_TOOLS:
                raise ValueError(f"{self.id} usa ferramenta DATA fora da allowlist")
            raw = _parameter_dict(self.expected_data_parameters)
            spec = TOOL_REGISTRY[self.expected_data_tool]
            validated = spec.arguments_model.model_validate(raw).model_dump(mode="json")
            if _canonical_json(raw) != _canonical_json(validated):
                raise ValueError(
                    f"{self.id} deve congelar argumentos DATA já normalizados com defaults"
                )
        elif self.expected_data_tool is not None or self.expected_data_parameters:
            raise ValueError(f"{self.id} não pode conter oracle DATA sem fonte DATA")

        if EvidenceSource.KNOWLEDGE in self.expected_sources:
            if not self.expected_knowledge_scopes:
                raise ValueError(f"{self.id} exige ao menos um scope KNOWLEDGE")
            if not self.expected_knowledge_temporal_statuses:
                raise ValueError(f"{self.id} exige temporalidade KNOWLEDGE")
            if not self.expected_knowledge_source_classes:
                raise ValueError(f"{self.id} exige ao menos uma source_class KNOWLEDGE")
            if SourceClass.WEB in self.expected_knowledge_source_classes:
                raise ValueError(f"{self.id} não pode classificar WEB como KNOWLEDGE")
        elif (
            self.expected_knowledge_scopes
            or self.expected_knowledge_temporal_statuses
            or self.expected_knowledge_source_classes
        ):
            raise ValueError(f"{self.id} não pode conter oracle KNOWLEDGE sem fonte KNOWLEDGE")

        if EvidenceSource.WEB in self.expected_sources:
            raw_web = _parameter_dict(self.expected_web_parameters)
            validated_web = WebQueryOptions.model_validate(raw_web).model_dump(mode="json")
            if _canonical_json(raw_web) != _canonical_json(validated_web):
                raise ValueError(
                    f"{self.id} deve congelar parâmetros WEB já normalizados com defaults"
                )
            if not bool(validated_web["official_only"]):
                raise ValueError(f"{self.id} exige official_only=true no holdout prospectivo")
            if validated_web["max_age_days"] is None:
                raise ValueError(f"{self.id} exige janela explícita de freshness")
        elif self.expected_web_parameters:
            raise ValueError(f"{self.id} não pode conter oracle WEB sem fonte WEB")

        return self


class OrchestrationHoldoutV2Suite(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    version: str = ORCHESTRATION_HOLDOUT_V2_VERSION
    cases: tuple[OrchestrationHoldoutV2Case, ...]

    @model_validator(mode="after")
    def validate_suite(self) -> "OrchestrationHoldoutV2Suite":
        if self.version != ORCHESTRATION_HOLDOUT_V2_VERSION:
            raise ValueError("Versão inesperada do Orchestration Holdout 2")
        if len(self.cases) != 56:
            raise ValueError("Orchestration Holdout 2.0.0 deve conter exatamente 56 casos")
        ids = [case.id for case in self.cases]
        if len(ids) != len(set(ids)):
            raise ValueError("IDs duplicados no Orchestration Holdout 2")
        expected_ids = [f"OH2-{index:03d}" for index in range(1, 57)]
        if ids != expected_ids:
            raise ValueError("IDs devem formar a sequência OH2-001..OH2-056")
        counts = Counter(case.category.value for case in self.cases)
        required = {category.value: 8 for category in OrchestrationHoldoutV2Category}
        if counts != required:
            raise ValueError(f"Categorias desbalanceadas: {dict(counts)}")
        return self


def _split(value: str) -> tuple[str, ...]:
    return tuple(item.strip() for item in value.split(";") if item.strip())


def _canonical_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _parameter_dict(parameters: tuple[EvidenceParameter, ...]) -> dict[str, object]:
    names = [parameter.name for parameter in parameters]
    if len(names) != len(set(names)):
        raise ValueError("Parâmetros duplicados no oracle")
    return {parameter.name: parameter.value for parameter in parameters}


def _parameters_from_json(value: str) -> tuple[EvidenceParameter, ...]:
    raw = json.loads(value or "{}")
    if not isinstance(raw, dict):
        raise ValueError("Campo de parâmetros deve ser objeto JSON")
    return tuple(
        EvidenceParameter(name=str(name), value=item)
        for name, item in sorted(raw.items())
    )


def _open_csv(path: Path):
    if path.suffix == ".gz":
        return gzip.open(path, "rt", encoding="utf-8-sig", newline="")
    return path.open("r", encoding="utf-8-sig", newline="")


def load_orchestration_holdout_v2(path: Path | str) -> OrchestrationHoldoutV2Suite:
    cases: list[OrchestrationHoldoutV2Case] = []
    with _open_csv(Path(path)) as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            payload: dict[str, object] = dict(row)
            payload["expected_sources"] = _split(str(payload.get("expected_sources", "")))
            tool = str(payload.get("expected_data_tool", "")).strip()
            payload["expected_data_tool"] = tool or None
            payload["expected_data_parameters"] = _parameters_from_json(
                str(payload.get("expected_data_parameters", "{}"))
            )
            payload["expected_knowledge_scopes"] = _split(
                str(payload.get("expected_knowledge_scopes", ""))
            )
            payload["expected_knowledge_temporal_statuses"] = _split(
                str(payload.get("expected_knowledge_temporal_statuses", ""))
            )
            payload["expected_knowledge_source_classes"] = _split(
                str(payload.get("expected_knowledge_source_classes", ""))
            )
            payload["expected_web_parameters"] = _parameters_from_json(
                str(payload.get("expected_web_parameters", "{}"))
            )
            notes = str(payload.get("notes", "")).strip()
            payload["notes"] = notes or None
            cases.append(OrchestrationHoldoutV2Case.model_validate(payload))
    return OrchestrationHoldoutV2Suite(cases=tuple(cases))


def orchestration_holdout_v2_sha256(path: Path | str) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def normalize_question_v2(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text.casefold())
    without_accents = "".join(
        char for char in decomposed if not unicodedata.combining(char)
    )
    return " ".join(re.findall(r"[a-z0-9]+", without_accents))


def questions_from_benchmark_v2(path: Path | str) -> tuple[str, ...]:
    benchmark = Path(path)
    if not benchmark.exists():
        raise ValueError(f"Benchmark histórico ausente: {benchmark}")
    with _open_csv(benchmark) as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames or "question" not in reader.fieldnames:
            raise ValueError(f"Benchmark histórico sem coluna question: {benchmark}")
        return tuple(str(row.get("question", "")) for row in reader)


def validate_frozen_prior_benchmarks_v2(
    paths: tuple[Path, ...] = FROZEN_PRIOR_BENCHMARK_PATHS,
) -> dict[str, object]:
    questions = 0
    for path in paths:
        questions += len(questions_from_benchmark_v2(path))
    return {
        "status": "PASS",
        "paths": [str(path) for path in paths],
        "benchmarks": len(paths),
        "questions": questions,
        "includes_oh1": Path(
            "data/benchmarks/orchestration_holdout_v1_0_0.csv.gz"
        ) in paths,
    }


def validate_orchestration_holdout_v2_novelty(
    suite: OrchestrationHoldoutV2Suite,
    prior_benchmark_paths: tuple[Path, ...] = FROZEN_PRIOR_BENCHMARK_PATHS,
    *,
    max_similarity_allowed: float = 0.70,
) -> dict[str, object]:
    current = {case.id: normalize_question_v2(case.question) for case in suite.cases}
    if len(set(current.values())) != len(current):
        raise ValueError("Há perguntas duplicadas após normalização dentro do OH2")

    prior: list[str] = []
    for path in prior_benchmark_paths:
        prior.extend(
            normalized
            for question in questions_from_benchmark_v2(path)
            if (normalized := normalize_question_v2(question))
        )

    prior_set = set(prior)
    exact = sorted(case_id for case_id, text in current.items() if text in prior_set)
    if exact:
        raise ValueError(f"Perguntas com repetição exata normalizada: {exact}")

    maxima: list[tuple[str, float]] = []
    for case_id, text in current.items():
        best = max(
            (SequenceMatcher(None, text, previous).ratio() for previous in prior),
            default=0.0,
        )
        maxima.append((case_id, best))
    maxima.sort(key=lambda item: item[1], reverse=True)
    highest = maxima[0][1] if maxima else 0.0
    if highest > max_similarity_allowed:
        offenders = [
            {"id": case_id, "similarity": similarity}
            for case_id, similarity in maxima
            if similarity > max_similarity_allowed
        ]
        raise ValueError(
            f"Similaridade acima do limite prospectivo {max_similarity_allowed}: {offenders}"
        )

    return {
        "status": "PASS",
        "new_cases": len(current),
        "prior_benchmarks_compared": len(prior_benchmark_paths),
        "prior_questions_compared": len(prior),
        "normalized_exact_overlap": 0,
        "max_similarity_allowed": max_similarity_allowed,
        "highest_sequence_similarity": highest,
        "highest_sequence_similarity_case": maxima[0][0] if maxima else None,
        "top_5_sequence_similarity": [
            {"id": case_id, "similarity": similarity}
            for case_id, similarity in maxima[:5]
        ],
    }


def validate_orchestration_holdout_v2_capabilities(
    suite: OrchestrationHoldoutV2Suite,
) -> dict[str, object]:
    source_counts = Counter(
        source.value for case in suite.cases for source in case.expected_sources
    )
    tool_counts = Counter(
        case.expected_data_tool.value
        for case in suite.cases
        if case.expected_data_tool is not None
    )
    web_cases = [
        case for case in suite.cases if EvidenceSource.WEB in case.expected_sources
    ]
    return {
        "status": "PASS",
        "cases": len(suite.cases),
        "category_counts": dict(Counter(case.category.value for case in suite.cases)),
        "source_presence_counts": dict(source_counts),
        "data_tool_counts": dict(tool_counts),
        "data_cases": source_counts.get("data", 0),
        "knowledge_cases": source_counts.get("knowledge", 0),
        "web_cases": source_counts.get("web", 0),
        "web_official_only_cases": len(web_cases),
        "web_explicit_freshness_window_cases": len(web_cases),
    }
