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
_UG_RE = re.compile(r"\bugs?\b")
_UG_CODE_RE = re.compile(r"\b\d{5,6}\b")


def _normalize(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text.casefold())
    return "".join(char for char in decomposed if not unicodedata.combining(char))


def _contains_any(text: str, terms: tuple[str, ...]) -> bool:
    return any(term in text for term in terms)


def _trail_tokens(text: str) -> set[str]:
    return set(_TRAIL_RE.findall(text))


def _mentions_ug(text: str) -> bool:
    return bool(_UG_RE.search(text)) or _contains_any(
        text,
        ("unidade gestora", "unidades gestoras"),
    )


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
            "prova ilegalidade",
            "comprova ",
            "comprovado",
            "comprovada",
            "significa que houve fraude",
            "significa fraude",
            "e irregular",
            "foi ilegal",
            "basta para afirmar",
            "suficiente para concluir",
            "autoriza concluir",
            "evidencia conclusiva",
            "permite acusar",
            "fraudou",
            "fraudador",
            "fraudulento",
            "fraude?",
            "fraude ?",
            "burlar a regra",
            "burlar o limite",
        ),
    )


def _route_composite(text: str) -> RouteDecision | None:
    """Combina camadas quando a pergunta pede dado/sinal e inferência categórica."""
    if not _is_categorical_challenge(text):
        return None

    if "fornecedor" in text and _contains_any(
        text,
        ("mais sinais", "topo", "ranking", "mais aparece", "maior recorrencia"),
    ):
        return _decision(
            Route.COMPOSITE,
            "ranking analítico combinado com pedido de interpretação categórica",
            EvidenceLayer.SERVING,
            EvidenceLayer.METHODOLOGY,
        )

    normative_topics = (
        "t01",
        "t05",
        "t08",
        "t09",
        "fim de semana",
        "final de semana",
        "fracionamento",
        "lei de benford",
        "benford",
        "limite legal",
        "perto do limite",
        "proximidade",
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


def _is_quantitative_request(text: str) -> bool:
    quantitative_cues = (
        "qual foi o valor",
        "qual o valor",
        "qual o montante",
        "qual apresentou mais",
        "quanto ",
        "quantas ",
        "quantos ",
        "quantifique",
        "mostre ",
        "exiba ",
        "liste ",
        "apresente ",
        "quero ver ",
        "quero comparar ",
        "compare ",
        "como evoluiram",
        "trajetoria anual",
        "evolucao dos gastos",
        "incidencia",
        "prevalencia",
        "ranking",
        "maior recorrencia",
        "maior frequencia",
        "mais sinais",
        "total desembolsado",
        "valor total",
        "montante de despesas",
        "foi movimentado",
        "maior valor",
        "quantidade de alertas",
        "quantidade de sinais",
    )
    return _contains_any(text, quantitative_cues)


def _route_methodology(text: str) -> RouteDecision | None:
    trails = _trail_tokens(text)
    explanation_cues = (
        "como funciona",
        "como e a trilha",
        "explique a trilha",
        "explique ",
        "descreva ",
        "qual regra",
        "regra operacional",
        "qual criterio",
        "criterio aplicado",
        "de que forma",
        "qual comportamento",
        "qual e o raciocinio",
        "raciocinio da",
        "por que ",
        "logica usada",
    )
    explains_trail = bool(trails) and _contains_any(text, explanation_cues)
    if explains_trail and not _is_quantitative_request(text):
        return _decision(
            Route.METHODOLOGY,
            "pedido de explicação do funcionamento ou critério de trilha",
            EvidenceLayer.METHODOLOGY,
            EvidenceLayer.KNOWLEDGE,
        )

    if _contains_any(text, ("metodologia", "metodo")):
        return _decision(
            Route.METHODOLOGY,
            "pedido metodológico explícito",
            EvidenceLayer.METHODOLOGY,
        )

    overlap_cues = (
        "sobrepos",
        "quase os mesmos alertas",
        "alertas muito parecidos",
        "eliminar uma delas",
        "excluir uma trilha",
    )
    if _contains_any(text, overlap_cues) and _contains_any(
        text,
        ("trilha", "alerta", "estatistic"),
    ):
        return _decision(
            Route.METHODOLOGY,
            "interpretação metodológica de sobreposição entre trilhas",
            EvidenceLayer.METHODOLOGY,
        )

    comparability_cues = (
        "comparar diretamente",
        "diretamente comparavel",
        "anos fechados",
        "ano incompleto",
        "ainda incompleto",
        "periodo parcial",
        "sem qualquer ressalva",
    )
    if _contains_any(text, comparability_cues) and _contains_any(
        text,
        ("2026", "periodo", "ano", "anos"),
    ):
        return _decision(
            Route.METHODOLOGY,
            "pedido de comparabilidade metodológica entre períodos",
            EvidenceLayer.METHODOLOGY,
        )

    if "t03" in trails and _contains_any(
        text,
        ("pagamento duplicado", "duplicidade", "coincidencia exata"),
    ):
        return _decision(
            Route.METHODOLOGY,
            "interpretação do alcance inferencial da T03",
            EvidenceLayer.METHODOLOGY,
        )

    if "t06" in trails and _contains_any(
        text,
        ("favorecimento", "favorecido", "acusar favorecimento"),
    ):
        return _decision(
            Route.METHODOLOGY,
            "interpretação do alcance inferencial da T06",
            EvidenceLayer.METHODOLOGY,
        )
    return None


def _route_data(text: str) -> RouteDecision | None:
    if not _is_quantitative_request(text):
        return None

    if _mentions_ug(text) and _UG_CODE_RE.search(text) and _contains_any(
        text,
        ("quanto ", "valor", "montante", "gastou", "gasto"),
    ):
        return _decision(
            Route.OVERVIEW,
            "consulta quantitativa sobre valor de UG específica",
            EvidenceLayer.SERVING,
        )

    territorial_terms = (
        "qual uf",
        " por uf",
        "estado",
        "territorial",
        "sao paulo",
        "mapa",
        "regiao",
        "unidade da federacao",
        "unidades da federacao",
    )
    if _contains_any(text, territorial_terms):
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

    if _mentions_ug(text):
        return _decision(
            Route.UGS,
            "consulta quantitativa por Unidade Gestora",
            EvidenceLayer.SERVING,
        )

    if _trail_tokens(text) or _contains_any(
        text,
        ("trilha", "prevalencia", "incidencia", "sinais", "alertas"),
    ):
        layers = (EvidenceLayer.SERVING,)
        if _contains_any(text, ("como devo interpretar", "explique como ler")):
            layers = (EvidenceLayer.SERVING, EvidenceLayer.METHODOLOGY)
        return _decision(Route.TRAILS, "consulta quantitativa de trilhas/sinais", *layers)

    return _decision(
        Route.OVERVIEW,
        "consulta quantitativa de visão geral",
        EvidenceLayer.SERVING,
    )


def _route_knowledge(text: str) -> RouteDecision | None:
    conceptual_starts = (
        "o que e ",
        "quem e ",
        "quem pode ",
        "quem responde ",
        "para que serve ",
        "qual e o papel ",
        "em que situacoes",
        "em quais hipoteses",
        "posso ",
        "e permitido ",
        "e possivel ",
        "ha alguma vedacao",
        "quando uma sequencia",
        "uma despesa ",
        "despesas repetidas",
        "um servidor ",
        "uma regra interna",
        "os valores de limite",
        "o tcu ",
        "como funciona a prestacao",
        "explique em termos simples",
        "a retirada de dinheiro",
    )
    domain_terms = (
        "cpgf",
        "cartao de pagamento do governo federal",
        "cartao corporativo federal",
        "suprimento de fundos",
        "agente suprido",
        "ordenador de despesa",
        "prestacao de contas",
        "saque",
        "dinheiro em especie",
        "fracionamento",
        "material permanente",
        "cartilha",
        "fiscalizacao continua",
        "parcelar uma aquisicao",
    )
    if text.startswith(conceptual_starts) or _contains_any(text, domain_terms):
        return _decision(
            Route.KNOWLEDGE,
            "pergunta conceitual/normativa sobre o domínio CPGF",
            EvidenceLayer.KNOWLEDGE,
        )
    return None


def _route_analytical_fallback(text: str) -> RouteDecision | None:
    """Preserva comandos analíticos autorizados fora das formas quantitativas principais."""
    if _contains_any(
        text,
        (
            "mapa",
            "territorial",
            "estado",
            "regiao",
            " por uf",
            "unidade da federacao",
            "unidades da federacao",
        ),
    ):
        return _decision(Route.TERRITORIAL, "termos territoriais", EvidenceLayer.SERVING)
    if "fornecedor" in text or "favorecido" in text:
        return _decision(Route.SUPPLIERS, "termos de fornecedor", EvidenceLayer.SERVING)
    if _mentions_ug(text):
        return _decision(Route.UGS, "termos de Unidade Gestora", EvidenceLayer.SERVING)
    if _trail_tokens(text) or _contains_any(text, ("trilha", "sinal", "alerta")):
        return _decision(Route.TRAILS, "termos de trilhas/sinais", EvidenceLayer.SERVING)
    if _contains_any(
        text,
        ("gasto", "despesa", "valor", "operacao", "resumo", "visao geral", "montante"),
    ):
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
