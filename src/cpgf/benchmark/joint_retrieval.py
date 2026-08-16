from __future__ import annotations

import csv
import hashlib
import re
import unicodedata
from collections import Counter
from difflib import SequenceMatcher
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from cpgf.ai.router import Route
from cpgf.knowledge import load_source_catalog
from cpgf.knowledge.models import CorpusScope, TemporalStatus

from .retrieval import RetrievalCategory

_CASE_ID = re.compile(r"^JH2-\d{3}$")
_TRAILS = {f"T{i:02d}" for i in range(1, 10)}
_LIST_FIELDS = {
    "gold_document_ids",
    "supporting_document_ids",
    "expected_scopes",
    "expected_temporal_statuses",
    "expected_trails",
}


class JointRetrievalHoldoutCase(BaseModel):
    """Oráculo congelado para o fluxo conjunto Router -> Retrieval Planner."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    category: RetrievalCategory
    question: str = Field(min_length=10, max_length=500)
    expected_route: Route
    gold_document_ids: tuple[str, ...]
    supporting_document_ids: tuple[str, ...] = ()
    expected_scopes: tuple[CorpusScope, ...]
    expected_temporal_statuses: tuple[TemporalStatus, ...]
    expected_trails: tuple[str, ...] = ()
    freshness_sensitive: bool = False
    notes: str | None = None

    @model_validator(mode="after")
    def validate_contract(self) -> "JointRetrievalHoldoutCase":
        if not _CASE_ID.fullmatch(self.id):
            raise ValueError(f"ID inválido: {self.id}")
        if not self.gold_document_ids:
            raise ValueError(f"{self.id} requer ao menos um documento-gabarito")
        if len(self.gold_document_ids) != len(set(self.gold_document_ids)):
            raise ValueError(f"Documentos-gabarito duplicados em {self.id}")
        if not self.expected_scopes:
            raise ValueError(f"{self.id} requer ao menos um escopo esperado")
        if not self.expected_temporal_statuses:
            raise ValueError(f"{self.id} requer ao menos uma temporalidade esperada")
        invalid_trails = sorted(set(self.expected_trails) - _TRAILS)
        if invalid_trails:
            raise ValueError(f"Trilhas inválidas em {self.id}: {invalid_trails}")
        if self.expected_route not in {Route.KNOWLEDGE, Route.METHODOLOGY, Route.COMPOSITE}:
            raise ValueError(
                f"{self.id} usa rota fora do universo documental do holdout: {self.expected_route}"
            )
        return self


class JointRetrievalHoldoutSuite(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    version: str = "2.0.0"
    cases: tuple[JointRetrievalHoldoutCase, ...]

    @model_validator(mode="after")
    def validate_suite(self) -> "JointRetrievalHoldoutSuite":
        if self.version != "2.0.0":
            raise ValueError("Versão do joint holdout deve ser 2.0.0")
        if len(self.cases) != 40:
            raise ValueError("Joint Retrieval Holdout 2.0.0 deve conter exatamente 40 casos")
        ids = [case.id for case in self.cases]
        if len(ids) != len(set(ids)):
            raise ValueError("IDs duplicados no joint holdout")
        categories = {case.category for case in self.cases}
        if categories != set(RetrievalCategory):
            raise ValueError("Joint holdout deve cobrir todas as categorias documentais")
        return self


def _split(value: str) -> tuple[str, ...]:
    return tuple(item.strip() for item in value.split(";") if item.strip())


def normalize_question(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text.casefold())
    without_accents = "".join(
        char for char in decomposed if not unicodedata.combining(char)
    )
    return " ".join(re.findall(r"[a-z0-9]+", without_accents))


def load_joint_retrieval_holdout(path: Path | str) -> JointRetrievalHoldoutSuite:
    cases: list[JointRetrievalHoldoutCase] = []
    with Path(path).open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            payload: dict[str, object] = dict(row)
            for field in _LIST_FIELDS:
                payload[field] = _split(str(payload.get(field, "")))
            payload["freshness_sensitive"] = (
                str(payload.get("freshness_sensitive", "")).strip() == "1"
            )
            notes = str(payload.get("notes", "")).strip()
            payload["notes"] = notes or None
            cases.append(JointRetrievalHoldoutCase.model_validate(payload))
    return JointRetrievalHoldoutSuite(cases=tuple(cases))


def joint_holdout_sha256(path: Path | str) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def validate_joint_holdout_against_catalog(
    suite: JointRetrievalHoldoutSuite,
    catalog_path: Path | str,
) -> dict[str, object]:
    catalog = load_source_catalog(Path(catalog_path))
    by_id = {item.document_id: item for item in catalog}
    gold = {document_id for case in suite.cases for document_id in case.gold_document_ids}
    referenced = {
        document_id
        for case in suite.cases
        for document_id in (*case.gold_document_ids, *case.supporting_document_ids)
    }
    missing = sorted(referenced - set(by_id))
    if missing:
        raise ValueError(f"Documentos ausentes do Knowledge: {missing}")

    non_default_gold = sorted(
        document_id
        for document_id in gold
        if not bool(by_id[document_id].retrieval_default)
    )
    if non_default_gold:
        raise ValueError(
            "Documento-gabarito fora da recuperação padrão: " + ", ".join(non_default_gold)
        )

    return {
        "status": "PASS",
        "cases": len(suite.cases),
        "category_counts": dict(Counter(case.category.value for case in suite.cases)),
        "expected_route_counts": dict(Counter(case.expected_route.value for case in suite.cases)),
        "gold_documents": len(gold),
        "referenced_documents": len(referenced),
        "freshness_sensitive_cases": sum(case.freshness_sensitive for case in suite.cases),
    }


def _questions_from_csv(path: Path) -> list[str]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return [str(row.get("question", "")) for row in csv.DictReader(handle)]


def validate_joint_holdout_novelty(
    suite: JointRetrievalHoldoutSuite,
    prior_benchmark_paths: list[Path] | tuple[Path, ...],
) -> dict[str, object]:
    current = {case.id: normalize_question(case.question) for case in suite.cases}
    if len(set(current.values())) != len(current):
        raise ValueError("Há perguntas duplicadas após normalização dentro do novo holdout")

    prior: list[tuple[str, str]] = []
    for path in prior_benchmark_paths:
        for question in _questions_from_csv(path):
            normalized = normalize_question(question)
            if normalized:
                prior.append((str(path), normalized))

    prior_texts = {text for _, text in prior}
    exact = sorted(case_id for case_id, text in current.items() if text in prior_texts)
    if exact:
        raise ValueError(f"Perguntas com repetição exata normalizada: {exact}")

    maxima: list[tuple[str, float]] = []
    for case_id, text in current.items():
        best = max(
            (SequenceMatcher(None, text, previous).ratio() for _, previous in prior),
            default=0.0,
        )
        maxima.append((case_id, best))
    maxima.sort(key=lambda item: item[1], reverse=True)

    return {
        "status": "PASS",
        "new_cases": len(current),
        "prior_questions_compared": len(prior),
        "normalized_exact_overlap": 0,
        "highest_sequence_similarity": maxima[0][1] if maxima else 0.0,
        "highest_sequence_similarity_case": maxima[0][0] if maxima else None,
        "top_5_sequence_similarity": [
            {"id": case_id, "similarity": similarity}
            for case_id, similarity in maxima[:5]
        ],
    }
