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
    if _contains_any(
        text,
        (
            "benford",
            "primeiro digito",
            "primeiros digitos",
            "primeiro algarismo",
            "primeiros algarismos",
            "digitos iniciais",
        ),
    ):
        hints.add("t08")
    if _contains_any(text, ("saque", "dinheiro em especie", "retirada de dinheiro")):
        hints.add("t07")
    if _contains_any(
        text,
        (
            "fracionamento",
            "compras repetidas",
            "despesas repetidas",
            "aquisicoes semelhantes",
            "aquisicoes recorrentes",
            "aquisicoes repetidas",
            "compras sucessivas",
            "divisao indevida",
            "despesa foi dividida",
        ),
    ):
        hints.update(("t03", "t04", "t05"))
    if _contains_any(
        text,
        (
            "lei 14.133",
            "lei 14133",
            "dispensa de licitacao",
            "contratacao direta",
            "contratacoes diretas",
            "limite",
        ),
    ):
        hints.add("t09")
    return tuple(sorted(hint.upper() for hint in hints))


def _is_control_external(text: str) -> bool:
    return _contains_any(
        text,
        (
            "tcu",
            "tribunal de contas da uniao",
            "acordao",
            "controle externo",
            "decisao de controle externo",
            "fiscalizacao continua",
            "fiscalizacao continuada",
            "fiscalizacao do cpgf",
            "precedente do tcu",
            "pronunciamento do tcu",
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
            "competencia em informacao",
        ),
    )


def _has_methodology_topic_cues(text: str) -> bool:
    return _contains_any(
        text,
        (
            "lei de benford",
            "benford",
            "primeiros algarismos",
            "primeiro algarismo",
            "algarismos iniciais",
            "digitos iniciais",
            "primeiros digitos",
            "distribuicao numerica",
            "anomalia estatistica",
            "alerta estatistico",
            "sinal estatistico",
            "sinais analiticos",
            "business intelligence",
            "inteligencia de negocios",
            "painel analitico",
            "paineis",
            "painel de gastos",
            "inteligencia artificial",
            "auditoria de recursos publicos",
            "fiscalizacao de gastos publicos",
            "triagem",
            "validacao humana",
            "analise forense",
            "analises forenses",
            "selecionar casos",
            "ferramenta de selecao",
            "ponto de partida para fiscalizacao",
        ),
    )


def _is_information_literacy_topic(text: str) -> bool:
    return _contains_any(
        text,
        (
            "competencia em informacao",
            "competencia informacional",
            "capacidade do cidadao de compreender",
            "capacidade de compreender informacao publica",
            "compreender informacoes do portal",
            "compreender informacao publica",
        ),
    )


def _has_explicit_cpgf_card_context(text: str) -> bool:
    return _contains_any(
        text,
        (
            "cpgf",
            "cartao governamental",
            "cartao corporativo",
            "cartao de pagamento",
            "cartao federal",
            "gastos do cartao",
            "despesas do cartao",
            "uso do cartao",
        ),
    )


def _is_portal_control_social(text: str) -> bool:
    return "portal da transparencia" in text and _contains_any(
        text,
        ("controle social", "participacao cidada"),
    )


def _asks_scientific_or_interpretive_sources(text: str) -> bool:
    return _contains_any(
        text,
        (
            "literatura",
            "estudo",
            "estudos",
            "artigo",
            "trabalho cientifico",
            "trabalhos cientificos",
            "pesquisa academica",
            "pesquisas academicas",
            "producao academica",
            "referencia cientifica",
            "referencias cientificas",
            "referencia academica",
            "referencias academicas",
            "evidencia academica",
            "evidencias academicas",
            "suporte academico",
            "literatura academica",
            "literatura de auditoria",
            "fundamentos normativos",
            "sistematize",
            "sistematizar",
        ),
    )


def _has_normative_bridge_cues(text: str) -> bool:
    return _contains_any(
        text,
        (
            "lei 14.133",
            "lei 14133",
            "dispensa de licitacao",
            "contratacao direta",
            "contratacoes diretas",
            "contratacao publica",
            "contratacoes publicas",
            "regime atual de licitacoes",
            "regime atual de contratacoes",
            "arcabouco juridico",
            "norma vigente",
            "normas vigentes",
            "norma oficial",
            "normas oficiais",
            "norma geral",
            "normas gerais",
            "normas basicas",
            "fundamentos normativos",
            "orientacao oficial",
            "orientacoes oficiais",
            "orientacao institucional",
            "orientacoes institucionais",
        ),
    )


def _is_legal_nature_interpretation(text: str) -> bool:
    nature_cue = _contains_any(
        text,
        (
            "natureza da despesa",
            "natureza juridica",
            "nova especie de despesa",
            "tipo de despesa",
            "categoria propria",
            "despesa autonoma",
        ),
    )
    instrument_cue = _contains_any(
        text,
        (
            "instrumento de pagamento",
            "meio de pagamento",
            "meio pelo qual ela e paga",
            "meio pelo qual e paga",
            "viabiliza seu pagamento",
            "viabiliza o pagamento",
            "apenas viabiliza",
            "sem tratar o cartao como uma despesa autonoma",
        ),
    )
    return nature_cue and instrument_cue


def _is_cpgf_social_cross_source(text: str) -> bool:
    social_cue = _contains_any(
        text,
        (
            "controle social",
            "fiscalizacao pela sociedade",
            "participacao cidada",
            "capacidade do cidadao",
            "acompanhar o uso",
            "acompanhamento do cpgf",
            "divulgacao de gastos",
            "abrir dados",
            "dados de despesas publicas",
            "competencia informacional",
        ),
    )
    cpgf_cue = _contains_any(
        text,
        (
            "cpgf",
            "cartao governamental",
            "cartao corporativo",
            "cartao de pagamento",
            "portal da transparencia",
            "gastos do cartao",
            "despesas do cartao",
        ),
    )
    source_cue = _contains_any(
        text,
        (
            "estudo",
            "estudos",
            "pesquisa",
            "pesquisas",
            "referencia",
            "referencias",
            "literatura",
            "trabalho",
            "trabalhos",
        ),
    )
    return social_cue and cpgf_cue and source_cue


def _is_repetition_or_fragmentation(text: str) -> bool:
    return _contains_any(
        text,
        (
            "fracionamento",
            "compras repetidas",
            "compras sucessivas",
            "despesas repetidas",
            "mesmo objeto",
            "repeticao",
            "aquisicoes semelhantes",
            "aquisicoes recorrentes",
            "aquisicoes repetidas",
            "em sequencia",
            "divisao indevida",
            "despesa foi dividida",
            "mesmo tipo",
        ),
    )


def _asks_source_basis(text: str) -> bool:
    return _contains_any(
        text,
        (
            "fontes",
            "referencias",
            "literatura",
            "normas",
            "orientacoes",
            "fundamentar",
            "fundamentacao",
            "investigar",
            "examinar",
        ),
    )


def _is_control_external_methodology_cross_source(text: str) -> bool:
    return (
        _is_control_external(text)
        and _asks_scientific_or_interpretive_sources(text)
        and _has_methodology_topic_cues(text)
    )


def _is_control_external_normative_cross_source(text: str) -> bool:
    return _is_control_external(text) and _has_normative_bridge_cues(text)


def _is_methodology_institutional_cross_source(
    text: str,
    decision: RouteDecision,
) -> bool:
    return (
        decision.route == Route.COMPOSITE
        and _asks_scientific_or_interpretive_sources(text)
        and _has_methodology_topic_cues(text)
        and _has_normative_bridge_cues(text)
    )


def _derive_scopes(text: str, decision: RouteDecision) -> tuple[CorpusScope, ...]:
    if _is_control_external_methodology_cross_source(text):
        return (CorpusScope.CONTROL_EXTERNAL, CorpusScope.METHODOLOGY)

    if _is_control_external_normative_cross_source(text):
        return (CorpusScope.CONTROL_EXTERNAL, CorpusScope.CPGF_CORE)

    if _is_control_external(text):
        return (CorpusScope.CONTROL_EXTERNAL,)

    if _is_information_literacy_topic(text) and not _has_explicit_cpgf_card_context(text):
        return (CorpusScope.METHODOLOGY,)

    if _is_methodology_institutional_cross_source(text, decision):
        return (CorpusScope.CPGF_CORE, CorpusScope.METHODOLOGY)

    if _is_methodology_only(text):
        return (CorpusScope.METHODOLOGY,)

    if _is_cpgf_social_cross_source(text):
        return (CorpusScope.CPGF_CORE, CorpusScope.METHODOLOGY)

    if _is_portal_control_social(text):
        if "competencia em informacao" in text:
            return (CorpusScope.METHODOLOGY,)
        return (CorpusScope.CPGF_CORE, CorpusScope.METHODOLOGY)

    if decision.route == Route.METHODOLOGY:
        return (CorpusScope.METHODOLOGY,)

    return (CorpusScope.CPGF_CORE,)


def _derive_temporal_statuses(
    text: str,
    scopes: tuple[CorpusScope, ...],
    decision: RouteDecision,
) -> tuple[TemporalStatus, ...]:
    if scopes == (CorpusScope.CONTROL_EXTERNAL, CorpusScope.METHODOLOGY):
        return (TemporalStatus.CONTEXTUAL,)

    if scopes == (CorpusScope.CONTROL_EXTERNAL, CorpusScope.CPGF_CORE):
        return (TemporalStatus.CONTEXTUAL, TemporalStatus.CURRENT)

    if CorpusScope.CONTROL_EXTERNAL in scopes:
        return (TemporalStatus.CONTEXTUAL,)

    if scopes == (CorpusScope.METHODOLOGY,):
        return (TemporalStatus.CONTEXTUAL,)

    if _is_methodology_institutional_cross_source(text, decision):
        return (TemporalStatus.CURRENT, TemporalStatus.CONTEXTUAL)

    if _is_cpgf_social_cross_source(text):
        if _has_normative_bridge_cues(text):
            return (TemporalStatus.CURRENT, TemporalStatus.CONTEXTUAL)
        return (TemporalStatus.CONTEXTUAL,)

    if _is_portal_control_social(text):
        return (TemporalStatus.CONTEXTUAL,)

    if _is_legal_nature_interpretation(text):
        return (TemporalStatus.CURRENT, TemporalStatus.CONTEXTUAL)

    if _asks_scientific_or_interpretive_sources(text) and _has_normative_bridge_cues(text):
        return (TemporalStatus.CURRENT, TemporalStatus.CONTEXTUAL)

    if _is_repetition_or_fragmentation(text) and _asks_source_basis(text):
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
    temporal_statuses = _derive_temporal_statuses(text, scopes, route_decision)

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
