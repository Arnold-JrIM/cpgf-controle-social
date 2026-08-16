from __future__ import annotations

import re
import unicodedata
from collections.abc import Callable

from pydantic import BaseModel, ConfigDict

from cpgf.ai.router import Route, RouteDecision, route_question
from cpgf.knowledge.models import CorpusScope, SourceClass, TemporalStatus


class RetrievalPlan(BaseModel):
    """Plano determinístico para limitar o universo documental antes da recuperação."""

    model_config = ConfigDict(frozen=True)

    route: Route
    scopes: tuple[CorpusScope, ...]
    temporal_statuses: tuple[TemporalStatus, ...]
    source_classes: tuple[SourceClass, ...] = ()
    trail_hints: tuple[str, ...] = ()
    reason: str
    deterministic: bool = True

    def search_filters(self) -> dict[str, set[str]]:
        filters: dict[str, set[str]] = {
            "scopes": {scope.value for scope in self.scopes},
            "temporal_statuses": {status.value for status in self.temporal_statuses},
        }
        if self.source_classes:
            filters["source_classes"] = {source_class.value for source_class in self.source_classes}
        return filters


Planner = Callable[[str], RetrievalPlan]


def _normalize(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text.casefold())
    return "".join(char for char in decomposed if not unicodedata.combining(char))


def _contains_any(text: str, terms: tuple[str, ...]) -> bool:
    return any(term in text for term in terms)


def _trail_hints(text: str) -> tuple[str, ...]:
    hints: set[str] = set(re.findall(r"\bt0[1-9]\b", text))
    if _contains_any(text, ("benford", "primeiro digito", "primeiros digitos")):
        hints.add("t08")
    if _contains_any(text, ("saque", "dinheiro em especie", "retirada de dinheiro")):
        hints.add("t07")
    if _contains_any(text, ("fracionamento", "compras repetidas", "despesas repetidas")):
        hints.update(("t03", "t04", "t05"))
    if _contains_any(text, ("lei 14.133", "lei 14133", "dispensa de licitacao", "limite")):
        hints.add("t09")
    return tuple(sorted(hint.upper() for hint in hints))


def _is_control_external(text: str) -> bool:
    return _contains_any(
        text,
        (
            "tcu",
            "tribunal de contas da uniao",
            "acordao",
            "fiscalizacao continua",
            "fiscalizacao do cpgf",
        ),
    )


def _is_methodology_only(text: str) -> bool:
    return _contains_any(
        text,
        (
            "lei de benford",
            "benford",
            "contabilidade forense",
            "business intelligence",
            "inteligencia artificial aplicada a auditoria",
            "inteligencia artificial aplicada à auditoria",
            "competencia em informacao",
            "competência em informação",
        ),
    )


def _is_portal_control_social(text: str) -> bool:
    return _contains_any(text, ("portal da transparencia", "portal da transparência")) and _contains_any(
        text,
        ("controle social", "participacao cidada", "participação cidadã"),
    )


def _asks_scientific_or_interpretive_sources(text: str) -> bool:
    return _contains_any(
        text,
        (
            "literatura",
            "estudo",
            "estudos",
            "artigo",
            "trabalho",
            "referencia cientifica",
            "referencias cientificas",
            "referência científica",
            "referências científicas",
            "literatura academica",
            "literatura acadêmica",
            "fundamentos normativos",
            "sistematize",
        ),
    )


def _is_repetition_or_fragmentation(text: str) -> bool:
    return _contains_any(
        text,
        (
            "fracionamento",
            "compras repetidas",
            "despesas repetidas",
            "mesmo objeto",
            "repeticao",
            "repetição",
        ),
    )


def _derive_scopes(text: str, decision: RouteDecision) -> tuple[CorpusScope, ...]:
    if _is_control_external(text):
        return (CorpusScope.CONTROL_EXTERNAL,)

    if _is_methodology_only(text):
        return (CorpusScope.METHODOLOGY,)

    if _is_portal_control_social(text):
        if _contains_any(text, ("competencia em informacao", "competência em informação")):
            return (CorpusScope.METHODOLOGY,)
        return (CorpusScope.CPGF_CORE, CorpusScope.METHODOLOGY)

    if decision.route == Route.METHODOLOGY:
        return (CorpusScope.METHODOLOGY,)

    return (CorpusScope.CPGF_CORE,)


def _derive_temporal_statuses(
    text: str,
    scopes: tuple[CorpusScope, ...],
) -> tuple[TemporalStatus, ...]:
    if CorpusScope.CONTROL_EXTERNAL in scopes:
        return (TemporalStatus.CONTEXTUAL,)

    if scopes == (CorpusScope.METHODOLOGY,):
        return (TemporalStatus.CONTEXTUAL,)

    if _is_portal_control_social(text):
        return (TemporalStatus.CONTEXTUAL,)

    if _asks_scientific_or_interpretive_sources(text):
        if _contains_any(
            text,
            (
                "lei 14.133",
                "lei 14133",
                "dispensa de licitacao",
                "dispensa de licitação",
                "fundamentos normativos",
            ),
        ):
            return (TemporalStatus.CURRENT, TemporalStatus.CONTEXTUAL)

    if _is_repetition_or_fragmentation(text) and _contains_any(
        text,
        ("fontes", "referencias", "referências", "fundamentar", "fundamentacao", "fundamentação"),
    ):
        return (TemporalStatus.CURRENT, TemporalStatus.CONTEXTUAL)

    return (TemporalStatus.CURRENT,)


def plan_knowledge_retrieval(
    question: str,
    *,
    decision: RouteDecision | None = None,
) -> RetrievalPlan:
    """Infere filtros do Knowledge sem consultar benchmark, golds ou metadados esperados."""
    route_decision = decision or route_question(question)
    text = _normalize(question)
    scopes = _derive_scopes(text, route_decision)
    temporal_statuses = _derive_temporal_statuses(text, scopes)

    return RetrievalPlan(
        route=route_decision.route,
        scopes=scopes,
        temporal_statuses=temporal_statuses,
        trail_hints=_trail_hints(text),
        reason=(
            "filtros inferidos deterministicamente a partir da pergunta e da rota; "
            "sem acesso ao gabarito do benchmark"
        ),
    )


class PlannedKnowledgeRetriever:
    """Aplica o plano em runtime antes de delegar a busca ao retriever subjacente."""

    def __init__(self, retriever: object, planner: Planner = plan_knowledge_retrieval):
        self._retriever = retriever
        self._planner = planner

    def search(self, query: str, *, limit: int = 5, **filters: object) -> list[object]:
        plan = self._planner(query)
        effective_filters: dict[str, object] = dict(plan.search_filters())
        effective_filters.update(filters)
        return self._retriever.search(query, limit=limit, **effective_filters)
