from __future__ import annotations

import re
import unicodedata
from enum import StrEnum

from pydantic import BaseModel, ConfigDict

from cpgf.ai.guardrails.input import validate_question


class Route(StrEnum):
    OVERVIEW = "overview"
    TRAILS = "trails"
    TERRITORIAL = "territorial"
    SUPPLIERS = "suppliers"
    UGS = "ugs"
    METHODOLOGY = "methodology"
    KNOWLEDGE = "knowledge"
    COMPOSITE = "composite"
    UNSUPPORTED = "unsupported"


class EvidenceLayer(StrEnum):
    SERVING = "serving"
    KNOWLEDGE = "knowledge"
    METHODOLOGY = "methodology"


class RouteDecision(BaseModel):
    model_config = ConfigDict(frozen=True)
    route: Route
    reason: str
    evidence_layers: tuple[EvidenceLayer, ...] = ()
    deterministic: bool = True


_TRAIL_RE = re.compile(r"\bt0[1-9]\b")


def _normalize(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text.casefold())
    return "".join(char for char in decomposed if not unicodedata.combining(char))


def _contains_any(text: str, terms: tuple[str, ...]) -> bool:
    return any(term in text for term in terms)


def _trail_tokens(text: str) -> set[str]:
    return set(_TRAIL_RE.findall(text))


def _decision(
    route: Route,
    reason: str,
    *layers: EvidenceLayer,
) -> RouteDecision:
    return RouteDecision(route=route, reason=reason, evidence_layers=layers)


def _is_categorical_challenge(text: str) -> bool:
    return _contains_any(
        text,
        (
            "prova que",
            "prova fraude",
            "significa que houve fraude",
            "significa fraude",
            "e irregular",
            "fraudou",
            "fraudador",
            "fraudulento",
            "fraude?",
            "fraude ?",
        ),
    )


def _route_composite(text: str) -> RouteDecision | None:
    """Identifica perguntas que exigem combinar camadas sem inferir conclusão substantiva."""
    if not _is_categorical_challenge(text):
        return None

    if "fornecedor" in text and _contains_any(text, ("mais sinais", "topo", "ranking")):
        return _decision(
            Route.COMPOSITE,
            "ranking analítico combinado com pedido de interpretação categórica",
            EvidenceLayer.SERVING,
            EvidenceLayer.METHODOLOGY,
        )

    normative_topics = (
        "fim de semana",
        "final de semana",
        "fracionamento",
        "lei de benford",
        "benford",
        "limite legal",
        "fugir do limite",
        "evasao de limite",
    )
    if _contains_any(text, normative_topics):
        return _decision(
            Route.COMPOSITE,
            "interpretação de sinal requer metodologia e evidência normativa/científica",
            EvidenceLayer.METHODOLOGY,
            EvidenceLayer.KNOWLEDGE,
        )
    return None


def _route_methodology(text: str) -> RouteDecision | None:
    trails = _trail_tokens(text)
    explains_trail = bool(trails) and _contains_any(
        text,
        ("como funciona", "como e a trilha", "explique a trilha"),
    )
    if explains_trail:
        return _decision(
            Route.METHODOLOGY,
            "pedido de explicação do funcionamento de trilha",
            EvidenceLayer.METHODOLOGY,
            EvidenceLayer.KNOWLEDGE,
        )

    if _contains_any(text, ("metodologia", "metodo")):
        return _decision(
            Route.METHODOLOGY,
            "pedido metodológico explícito",
            EvidenceLayer.METHODOLOGY,
        )

    if "sobrepos" in text and _contains_any(text, ("trilha", "estatistic")):
        return _decision(
            Route.METHODOLOGY,
            "interpretação metodológica de sobreposição entre trilhas",
            EvidenceLayer.METHODOLOGY,
        )

    if _contains_any(text, ("comparar diretamente", "diretamente comparavel")):
        return _decision(
            Route.METHODOLOGY,
            "pedido de comparabilidade metodológica entre períodos",
            EvidenceLayer.METHODOLOGY,
        )

    if "t03" in trails and _contains_any(text, ("pagamento duplicado", "duplicidade")):
        return _decision(
            Route.METHODOLOGY,
            "interpretação do alcance inferencial da T03",
            EvidenceLayer.METHODOLOGY,
        )

    if "t06" in trails and _contains_any(text, ("favorecimento", "favorecido")):
        return _decision(
            Route.METHODOLOGY,
            "interpretação do alcance inferencial da T06",
            EvidenceLayer.METHODOLOGY,
        )
    return None


def _is_data_query(text: str) -> bool:
    prefixes = (
        "qual foi o valor",
        "qual uf",
        "quais ug",
        "quais forneced",
        "quais trilhas",
        "quantas",
        "quantos",
        "quanto ",
        "como evoluiram",
        "compare a prevalencia",
    )
    return text.startswith(prefixes)


def _route_data(text: str) -> RouteDecision | None:
    if not _is_data_query(text):
        return None

    if _contains_any(text, ("qual foi o valor", "quantas operacoes", "quanto ", "como evoluiram")):
        return _decision(
            Route.OVERVIEW,
            "consulta quantitativa de visão geral",
            EvidenceLayer.SERVING,
        )

    if _contains_any(
        text,
        ("qual uf", " por uf", "estado", "territorial", "sao paulo", "mapa", "regiao"),
    ):
        return _decision(
            Route.TERRITORIAL,
            "consulta quantitativa territorial",
            EvidenceLayer.SERVING,
        )

    if "fornecedor" in text or "favorecido" in text:
        return _decision(
            Route.SUPPLIERS,
            "consulta quantitativa por fornecedor",
            EvidenceLayer.SERVING,
        )

    if re.search(r"\bugs?\b", text) or "unidade gestora" in text:
        return _decision(
            Route.UGS,
            "consulta quantitativa por Unidade Gestora",
            EvidenceLayer.SERVING,
        )

    if _trail_tokens(text) or _contains_any(text, ("trilha", "prevalencia", "sinais")):
        layers = (EvidenceLayer.SERVING,)
        if "como devo interpretar" in text:
            layers = (EvidenceLayer.SERVING, EvidenceLayer.METHODOLOGY)
        return _decision(Route.TRAILS, "consulta quantitativa de trilhas/sinais", *layers)

    return _decision(Route.OVERVIEW, "consulta quantitativa geral", EvidenceLayer.SERVING)


def _route_knowledge(text: str) -> RouteDecision | None:
    conceptual_starts = (
        "o que e ",
        "quem e ",
        "quem pode ",
        "em que situacoes",
        "posso ",
        "e permitido ",
        "e possivel ",
        "uma despesa ",
        "despesas repetidas",
        "um servidor ",
        "uma regra interna",
        "os valores de limite",
        "o tcu ",
        "como funciona a prestacao",
    )
    domain_terms = (
        "cpgf",
        "suprimento de fundos",
        "agente suprido",
        "ordenador de despesa",
        "prestacao de contas",
        "unidade gestora",
        "saque",
        "fracionamento",
        "material permanente",
        "cartilha",
        "fiscalizacao continua",
    )
    if text.startswith(conceptual_starts) or _contains_any(text, domain_terms):
        return _decision(
            Route.KNOWLEDGE,
            "pergunta conceitual/normativa sobre o domínio CPGF",
            EvidenceLayer.KNOWLEDGE,
        )
    return None


def _route_analytical_fallback(text: str) -> RouteDecision | None:
    """Preserva comandos analíticos autorizados que não usam a forma interrogativa do benchmark."""
    if _contains_any(text, ("mapa", "territorial", "estado", "regiao", " por uf")):
        return _decision(Route.TERRITORIAL, "termos territoriais", EvidenceLayer.SERVING)
    if "fornecedor" in text or "favorecido" in text:
        return _decision(Route.SUPPLIERS, "termos de fornecedor", EvidenceLayer.SERVING)
    if re.search(r"\bugs?\b", text):
        return _decision(Route.UGS, "termos de Unidade Gestora", EvidenceLayer.SERVING)
    if _trail_tokens(text) or _contains_any(text, ("trilha", "sinal", "alerta")):
        return _decision(Route.TRAILS, "termos de trilhas/sinais", EvidenceLayer.SERVING)
    if _contains_any(text, ("gasto", "despesa", "valor", "operacao", "resumo", "visao geral")):
        return _decision(Route.OVERVIEW, "termos de visão geral", EvidenceLayer.SERVING)
    return None


def route_question(question: str) -> RouteDecision:
    """Roteamento determinístico por intenção, sem LLM e sem execução automática de ferramentas."""
    validated = validate_question(question)
    text = _normalize(validated)

    for classifier in (
        _route_composite,
        _route_methodology,
        _route_data,
        _route_knowledge,
        _route_analytical_fallback,
    ):
        decision = classifier(text)
        if decision is not None:
            return decision

    return _decision(
        Route.UNSUPPORTED,
        "nenhuma intenção autorizada foi identificada de forma determinística",
    )
