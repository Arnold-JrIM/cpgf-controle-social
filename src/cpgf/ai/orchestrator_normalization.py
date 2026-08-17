from __future__ import annotations

import copy
import re
import unicodedata
from dataclasses import dataclass
from typing import Any

from cpgf.ai.evidence_workers import DEFAULT_KNOWLEDGE_LIMIT
from cpgf.ai.web_evidence import DEFAULT_WEB_LIMIT, MAX_WEB_LIMIT
from cpgf.knowledge.models import CorpusScope, SourceClass, TemporalStatus

ORCHESTRATOR_NORMALIZATION_VERSION = "1.0.0"


@dataclass(frozen=True)
class NormalizationResult:
    payload: dict[str, object]
    notes: tuple[str, ...]


def _ascii_text(*values: object) -> str:
    text = " ".join(str(value) for value in values if value is not None)
    normalized = unicodedata.normalize("NFKD", text.lower())
    return normalized.encode("ascii", "ignore").decode("ascii")


def _contains_any(text: str, terms: tuple[str, ...]) -> bool:
    return any(term in text for term in terms)


def _section(payload: dict[str, object], name: str) -> dict[str, Any] | None:
    value = payload.get(name)
    return value if isinstance(value, dict) else None


def _clear_source(section: dict[str, Any], source: str) -> None:
    section["selected"] = False
    section["objective"] = None
    section["parameters"] = []
    if source == "data":
        section["tool"] = None
    elif source == "knowledge":
        section["query_hint"] = None
        section["scopes"] = []
        section["temporal_statuses"] = []
        section["source_classes"] = []
    elif source == "web":
        section["query_hint"] = None
        section["freshness_required"] = False


def _parameters(values: object) -> dict[str, object]:
    if not isinstance(values, (list, tuple)):
        return {}
    result: dict[str, object] = {}
    conflicts: set[str] = set()
    for item in values:
        if not isinstance(item, dict):
            continue
        name = item.get("name")
        if not isinstance(name, str):
            continue
        value = item.get("value")
        if name in result and result[name] != value:
            conflicts.add(name)
        result[name] = value
    for name in conflicts:
        result.pop(name, None)
    return result


def _parameter_list(values: dict[str, object]) -> list[dict[str, object]]:
    return [{"name": name, "value": value} for name, value in sorted(values.items())]


def _governed_knowledge_intent(question: str) -> bool:
    text = _ascii_text(question)
    markers = (
        "corpus",
        "documentacao do projeto",
        "base normativa",
        "fundamento jurid",
        "referenc",
        "literatura",
        "orientacao institucional",
        "entendimento de controle externo",
        "fontes do projeto",
    )
    return _contains_any(text, markers)


def _explicit_recency_days(text: str) -> int | None:
    normalized = _ascii_text(text)
    patterns = (
        (r"\bultim(?:o|os|a|as)\s+(\d{1,4})\s+dias?\b", 1),
        (r"\bultim(?:o|os|a|as)\s+(\d{1,3})\s+semanas?\b", 7),
        (r"\bultim(?:o|os|a|as)\s+(\d{1,2})\s+mes(?:es)?\b", 30),
        (r"\bultim(?:o|os|a|as)\s+(\d{1,2})\s+anos?\b", 365),
    )
    for pattern, multiplier in patterns:
        match = re.search(pattern, normalized)
        if match:
            days = int(match.group(1)) * multiplier
            return days if 1 <= days <= 3650 else None
    return None


def _requested_result_limit(text: str, *, maximum: int, default: int) -> int:
    normalized = _ascii_text(text)
    match = re.search(
        r"\b(?:traga|liste|mostre|recupere|cite)\s+(?:as?\s+)?(\d{1,2})\s+"
        r"(?:fontes|referencias|documentos|estudos|artigos|resultados|links|publicacoes)\b",
        normalized,
    )
    if not match:
        return default
    value = int(match.group(1))
    return value if 1 <= value <= maximum else default


def _official_only_requested(text: str) -> bool:
    normalized = _ascii_text(text)
    return _contains_any(
        normalized,
        (
            "fonte oficial",
            "fontes oficiais",
            "pagina oficial",
            "paginas oficiais",
            "publicacao oficial",
            "comunicado oficial",
            "orientacao oficial",
            "disponibilizada oficialmente",
            "anunciada oficialmente",
            "governo federal",
            "tcu",
            "cgu",
            "gov.br",
        ),
    )


def _knowledge_source_classes(text: str, raw: tuple[str, ...]) -> tuple[str, ...]:
    normalized = _ascii_text(text)

    control = _contains_any(
        normalized,
        (
            "controle externo",
            "tcu",
            "acordao",
            "decisao de controle",
            "entendimento de controle",
        ),
    )
    scholarly = _contains_any(
        normalized,
        (
            "literatura",
            "estudo",
            "referenc",
            "metodolog",
            "lei de benford",
            "transparencia",
            "competencia informacional",
            "testes digitais",
        ),
    )
    project_method = _contains_any(
        normalized,
        (
            "leitura territorial",
            "interpretacao geografica",
            "contexto territorial",
        ),
    )
    institutional = _contains_any(
        normalized,
        (
            "orientacao institucional",
            "guia institucional",
            "manual",
            "ciclo operacional",
            "responsabilidades do agente",
            "normas e guias",
        ),
    )
    normative = _contains_any(
        normalized,
        (
            "norma",
            "normativ",
            "fundamento jurid",
            "juridic",
            "fracionamento",
            "divisao indevida",
            "contratacao direta",
            "regime do suprimento",
            "valores-limite",
        ),
    )
    payment_concept = _contains_any(
        normalized,
        (
            "instrumento de pagamento",
            "meio de pagamento",
            "modalidade autonoma",
        ),
    )
    alert_review = _contains_any(
        normalized,
        (
            "alertas automatizados",
            "revisao humana",
            "exame posterior",
            "sinais de exame",
        ),
    )
    repetition_caution = "repeticao de compras" in normalized and "cautela" in normalized

    inferred: set[str] = set()
    if scholarly:
        inferred.update((SourceClass.ACADEMIC.value, SourceClass.SCIENTIFIC.value))
    if project_method:
        inferred.update((SourceClass.PROJECT.value, SourceClass.SCIENTIFIC.value))
    if control and not scholarly:
        inferred.add(SourceClass.CONTROL_EXTERNAL.value)
    if institutional:
        inferred.add(SourceClass.INSTITUTIONAL.value)
    if normative:
        inferred.add(SourceClass.NORMATIVE.value)
    if payment_concept:
        inferred.update((SourceClass.ACADEMIC.value, SourceClass.NORMATIVE.value))
    if alert_review and not scholarly:
        inferred.update((SourceClass.INSTITUTIONAL.value, SourceClass.SCIENTIFIC.value))
    if repetition_caution:
        inferred.update(
            (
                SourceClass.ACADEMIC.value,
                SourceClass.NORMATIVE.value,
                SourceClass.SCIENTIFIC.value,
            )
        )
    if institutional and _contains_any(normalized, ("responsabilidades", "comprovacao")):
        inferred.add(SourceClass.NORMATIVE.value)

    if inferred:
        return tuple(sorted(inferred))

    allowed = {source_class.value for source_class in SourceClass if source_class is not SourceClass.WEB}
    return tuple(dict.fromkeys(value for value in raw if value in allowed))


def _knowledge_scopes(text: str, raw: tuple[str, ...]) -> tuple[str, ...]:
    normalized = _ascii_text(text)
    inferred: set[str] = set()

    control = _contains_any(
        normalized,
        ("controle externo", "tcu", "acordao", "entendimento de controle"),
    )
    methodology = _contains_any(
        normalized,
        (
            "metodolog",
            "literatura",
            "estudo",
            "referenc",
            "lei de benford",
            "transparencia",
            "competencia informacional",
            "testes digitais",
            "ranking analitico",
            "alertas automatizados",
            "revisao humana",
            "leitura territorial",
            "interpretacao geografica",
            "cautela na analise",
        ),
    )
    core = _contains_any(
        normalized,
        (
            "suprimento de fundos",
            "agente suprido",
            "prestacao de contas",
            "uso excepcional de saque",
            "fracionamento",
            "divisao indevida",
            "repeticao de compras",
            "instrumento de pagamento",
            "meio de pagamento",
            "modalidade autonoma",
            "regime do suprimento",
            "valores-limite",
        ),
    )

    if control:
        inferred.add(CorpusScope.CONTROL_EXTERNAL.value)
    if methodology:
        inferred.add(CorpusScope.METHODOLOGY.value)
    if core:
        inferred.add(CorpusScope.CPGF_CORE.value)
    if "alertas automatizados" in normalized:
        inferred.add(CorpusScope.CPGF_CORE.value)
    if _contains_any(normalized, ("marinha", "naval", "institucional mb")):
        inferred.add(CorpusScope.INSTITUTIONAL_MB.value)
    if _contains_any(normalized, ("historico", "historica", "vigencia anterior")):
        inferred.add(CorpusScope.HISTORICAL.value)
    if _contains_any(normalized, ("descobrir no corpus", "explorar o corpus")):
        inferred.add(CorpusScope.DISCOVERY.value)

    if inferred:
        return tuple(sorted(inferred))

    if "cpgf" in normalized or "cartao" in normalized:
        return (CorpusScope.CPGF_CORE.value,)

    allowed = {scope.value for scope in CorpusScope}
    return tuple(dict.fromkeys(value for value in raw if value in allowed))


def _knowledge_temporal_statuses(
    text: str,
    source_classes: tuple[str, ...],
    raw: tuple[str, ...],
) -> tuple[str, ...]:
    normalized = _ascii_text(text)
    inferred: set[str] = set()
    classes = set(source_classes)

    if _contains_any(normalized, ("historico", "historica", "vigencia anterior", "a epoca")):
        inferred.add(TemporalStatus.HISTORICAL.value)

    if classes & {SourceClass.NORMATIVE.value, SourceClass.INSTITUTIONAL.value}:
        inferred.add(TemporalStatus.CURRENT.value)
    if classes & {
        SourceClass.ACADEMIC.value,
        SourceClass.SCIENTIFIC.value,
        SourceClass.PROJECT.value,
        SourceClass.CONTROL_EXTERNAL.value,
    }:
        inferred.add(TemporalStatus.CONTEXTUAL.value)

    if _contains_any(
        normalized,
        ("vigente", "atual", "responsabilidades", "ciclo operacional", "regime"),
    ):
        inferred.add(TemporalStatus.CURRENT.value)
    if _contains_any(
        normalized,
        ("contextual", "cautela", "triagem", "interpret", "uso excepcional"),
    ):
        inferred.add(TemporalStatus.CONTEXTUAL.value)

    if inferred:
        return tuple(sorted(inferred))

    allowed = {status.value for status in TemporalStatus}
    retained = [value for value in raw if value in allowed]
    if TemporalStatus.HISTORICAL.value in retained and "histor" not in normalized:
        retained = [value for value in retained if value != TemporalStatus.HISTORICAL.value]
    if retained:
        return tuple(dict.fromkeys(retained))
    return ()


def _normalize_knowledge(
    question: str,
    section: dict[str, Any],
    notes: list[str],
) -> None:
    if section.get("selected") is not True:
        before = copy.deepcopy(section)
        _clear_source(section, "knowledge")
        if section != before:
            notes.append("NORMALIZED_UNSELECTED_KNOWLEDGE")
        return

    if not section.get("objective"):
        section["objective"] = "Recuperar evidência documental governada pertinente à pergunta."
        notes.append("FILLED_KNOWLEDGE_OBJECTIVE")
    if not section.get("query_hint"):
        section["query_hint"] = question.strip()
        notes.append("FILLED_KNOWLEDGE_QUERY_HINT")

    basis = _ascii_text(section.get("objective"), section.get("query_hint"))
    raw_scopes = tuple(str(value) for value in section.get("scopes", []) if isinstance(value, str))
    raw_temporal = tuple(
        str(value) for value in section.get("temporal_statuses", []) if isinstance(value, str)
    )
    raw_classes = tuple(
        str(value) for value in section.get("source_classes", []) if isinstance(value, str)
    )

    classes = _knowledge_source_classes(basis, raw_classes)
    scopes = _knowledge_scopes(basis, raw_scopes)
    temporal = _knowledge_temporal_statuses(basis, classes, raw_temporal)

    if list(classes) != section.get("source_classes"):
        section["source_classes"] = list(classes)
        notes.append("CANONICALIZED_KNOWLEDGE_SOURCE_CLASSES")
    if list(scopes) != section.get("scopes"):
        section["scopes"] = list(scopes)
        notes.append("CANONICALIZED_KNOWLEDGE_SCOPES")
    if list(temporal) != section.get("temporal_statuses"):
        section["temporal_statuses"] = list(temporal)
        notes.append("CANONICALIZED_KNOWLEDGE_TEMPORAL")

    limit = _requested_result_limit(
        basis,
        maximum=20,
        default=DEFAULT_KNOWLEDGE_LIMIT,
    )
    parameters = {"limit": limit}
    if _parameter_list(parameters) != section.get("parameters"):
        section["parameters"] = _parameter_list(parameters)
        notes.append("CANONICALIZED_KNOWLEDGE_PARAMETERS")


def _normalize_web(
    question: str,
    section: dict[str, Any],
    notes: list[str],
) -> None:
    if section.get("selected") is not True:
        before = copy.deepcopy(section)
        _clear_source(section, "web")
        if section != before:
            notes.append("NORMALIZED_UNSELECTED_WEB")
        return

    if not section.get("objective"):
        section["objective"] = "Recuperar evidência externa atual necessária para responder à pergunta."
        notes.append("FILLED_WEB_OBJECTIVE")
    if not section.get("query_hint"):
        section["query_hint"] = question.strip()
        notes.append("FILLED_WEB_QUERY_HINT")
    if section.get("freshness_required") is not True:
        section["freshness_required"] = True
        notes.append("ENFORCED_WEB_FRESHNESS")

    basis = _ascii_text(question, section.get("objective"), section.get("query_hint"))
    raw = _parameters(section.get("parameters"))
    limit = _requested_result_limit(basis, maximum=MAX_WEB_LIMIT, default=DEFAULT_WEB_LIMIT)
    official_only = _official_only_requested(basis)
    if not official_only and isinstance(raw.get("official_only"), bool):
        official_only = bool(raw["official_only"])
    max_age_days = _explicit_recency_days(basis)

    parameters: dict[str, object] = {
        "limit": limit,
        "official_only": official_only,
        "max_age_days": max_age_days,
    }
    if _parameter_list(parameters) != section.get("parameters"):
        section["parameters"] = _parameter_list(parameters)
        notes.append("CANONICALIZED_WEB_PARAMETERS")


def normalize_orchestrator_payload(
    question: str,
    payload: dict[str, object],
) -> NormalizationResult:
    """Aplica política determinística, auditável e idempotente ao draft semântico do LLM."""
    normalized = copy.deepcopy(payload)
    notes: list[str] = []

    clarification = normalized.get("clarification_question")
    if isinstance(clarification, str) and clarification.strip():
        for source in ("data", "knowledge", "web"):
            section = _section(normalized, source)
            if section is not None and section.get("selected") is True:
                _clear_source(section, source)
                notes.append("CLARIFICATION_FAIL_CLOSED")

    data = _section(normalized, "data")
    if data is not None and data.get("selected") is not True:
        before = copy.deepcopy(data)
        _clear_source(data, "data")
        if data != before:
            notes.append("NORMALIZED_UNSELECTED_DATA")

    knowledge = _section(normalized, "knowledge")
    web = _section(normalized, "web")
    if (
        knowledge is not None
        and web is not None
        and knowledge.get("selected") is True
        and web.get("selected") is True
        and not _governed_knowledge_intent(question)
    ):
        _clear_source(knowledge, "knowledge")
        notes.append("DROPPED_KNOWLEDGE_WITHOUT_GOVERNED_INTENT")

    if knowledge is not None:
        _normalize_knowledge(question, knowledge, notes)
    if web is not None:
        _normalize_web(question, web, notes)

    return NormalizationResult(
        payload=normalized,
        notes=tuple(dict.fromkeys(notes)),
    )
