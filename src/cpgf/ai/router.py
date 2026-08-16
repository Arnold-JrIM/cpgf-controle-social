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
_UF_CODES = frozenset(
    {
        "ac",
        "al",
        "am",
        "ap",
        "ba",
        "ce",
        "df",
        "es",
        "go",
        "ma",
        "mg",
        "ms",
        "mt",
        "pa",
        "pb",
        "pe",
        "pi",
        "pr",
        "rj",
        "rn",
        "ro",
        "rr",
        "rs",
        "sc",
        "se",
        "sp",
        "to",
    }
)


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


def _mentions_multiple_uf_codes(text: str) -> bool:
    tokens = set(re.findall(r"\b[a-z]{2}\b", text))
    return len(tokens.intersection(_UF_CODES)) >= 2


def _decision(
    route: Route,
    reason: str,
    *layers: EvidenceLayer,
) -> RouteDecision:
    return RouteDecision(route=route, reason=reason, evidence_layers=layers)


def _asks_scientific_sources(text: str) -> bool:
    return _contains_any(
        text,
        (
            "base academica",
            "base cientifica",
            "fundamento cientifico",
            "fundamentos cientificos",
            "suporte academico",
            "evidencia academica",
            "evidencias academicas",
            "pesquisa academica",
            "pesquisas academicas",
            "pesquisa recente",
            "pesquisas recentes",
            "referencia academica",
            "referencias academicas",
            "referencia cientifica",
            "referencias cientificas",
            "referencia tecnica",
            "referencias tecnicas",
            "trabalho academico",
            "trabalhos academicos",
            "trabalho cientifico",
            "trabalhos cientificos",
            "trabalho empirico",
            "trabalhos empiricos",
            "estudo academico",
            "estudos academicos",
            "estudo cientifico",
            "estudos cientificos",
            "estudo recente",
            "estudos recentes",
            "aplicacao empirica",
            "aplicacoes empiricas",
            "producao academica",
            "literatura academica",
            "literatura cientifica",
            "literatura de auditoria",
            "que literatura",
            "literatura pode",
            "literatura sobre",
            "que estudo",
            "que pesquisa",
            "qual pesquisa",
            "quais pesquisas",
            "quais estudos",
            "quais trabalhos",
        ),
    )


def _has_normative_cross_source_cues(text: str) -> bool:
    return _contains_any(
        text,
        (
            "arcabouco juridico",
            "regime atual de contratacoes",
            "regime atual de licitacoes",
            "norma vigente",
            "normas vigentes",
            "norma oficial",
            "normas oficiais",
            "norma geral",
            "normas gerais",
            "normas basicas",
            "fonte normativa",
            "fontes normativas",
            "referencia normativa",
            "referencias normativas",
            "orientacao oficial",
            "orientacoes oficiais",
            "orientacao institucional",
            "orientacoes institucionais",
            "contratacao direta",
            "contratacoes diretas",
            "contratacao publica",
            "contratacoes publicas",
            "licitacao",
            "lei 14.133",
            "lei 14133",
        ),
    )


def _has_control_external_cues(text: str) -> bool:
    return _contains_any(
        text,
        (
            "tcu",
            "tribunal de contas da uniao",
            "acordao",
            "controle externo",
            "decisao de controle externo",
            "precedente do tcu",
            "pronunciamento do tcu",
        ),
    )


def _has_control_social_cross_source_cues(text: str) -> bool:
    social_cue = _contains_any(
        text,
        (
            "controle social",
            "fiscalizacao pela sociedade",
            "participacao cidada",
            "capacidade do cidadao",
            "acompanhar o uso",
            "abrir dados",
            "dados de despesas publicas",
            "divulgacao de gastos",
            "transparencia governamental",
            "competencia informacional",
            "competencia em informacao",
        ),
    )
    cpgf_cue = _contains_any(
        text,
        (
            "cpgf",
            "cartao governamental",
            "cartao corporativo",
            "cartao de pagamento",
            "gastos do cartao",
            "despesas do cartao",
        ),
    )
    return social_cue and cpgf_cue


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
            "suficiente para rotular",
            "e suficiente para",
            "autoriza concluir",
            "autoriza dizer",
            "permite concluir",
            "permite afirmar",
            "permite dizer",
            "posso concluir",
            "pode ser chamada de",
            "por si so demonstra",
            "por si so comprova",
            "evidencia conclusiva",
            "permite acusar",
            "fraudou",
            "fraudador",
            "fraudulento",
            "fraudulenta",
            "fraudulentas",
            "fraude?",
            "fraude ?",
            "houve ilicito",
            "burlar a regra",
            "burlar o limite",
            "contornar a norma",
            "tentativa deliberada",
        ),
    )


def _route_composite(text: str) -> RouteDecision | None:
    """Combina camadas quando a pergunta exige mais de uma família de evidência."""
    scientific_sources = _asks_scientific_sources(text)
    normative_sources = _has_normative_cross_source_cues(text)
    control_social_sources = _has_control_social_cross_source_cues(text)
    control_external_sources = _has_control_external_cues(text)

    if scientific_sources and (
        normative_sources or control_social_sources or control_external_sources
    ):
        return _decision(
            Route.COMPOSITE,
            "pergunta documental combina literatura com outra família de evidência",
            EvidenceLayer.METHODOLOGY,
            EvidenceLayer.KNOWLEDGE,
        )

    if control_external_sources and normative_sources:
        return _decision(
            Route.COMPOSITE,
            "pergunta combina decisão de controle externo com base normativa",
            EvidenceLayer.KNOWLEDGE,
        )

    if control_social_sources and _contains_any(
        text,
        ("competencia informacional", "competencia em informacao"),
    ):
        return _decision(
            Route.COMPOSITE,
            "pergunta combina transparência do CPGF com capacidade informacional",
            EvidenceLayer.METHODOLOGY,
            EvidenceLayer.KNOWLEDGE,
        )

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
        "informe ",
        "mostre ",
        "exiba ",
        "liste ",
        "apresente ",
        "quero ver ",
        "quero comparar ",
        "compare ",
        "como evoluiram",
        "trajetoria anual",
        "evolucao anual",
        "evolucao dos gastos",
        "serie anual",
        "incidencia",
        "prevalencia",
        "ranking",
        "maior recorrencia",
        "maior frequencia",
        "mais sinais",
        "total desembolsado",
        "valor agregado",
        "valor total",
        "gasto total",
        "montante de despesas",
        "foi movimentado",
        "maior valor",
        "quantidade de alertas",
        "quantidade de sinais",
        "quantidade de operacoes",
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
        "que condicao",
        "condicao operacional",
        "por qual motivo",
        "de que forma",
        "como a ",
        "o que a ",
        "qual padrao",
        "em que consiste",
        "qual e a logica",
        "que papel",
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

    benford_paraphrases = (
        "lei de benford",
        "benford",
        "primeiros algarismos",
        "primeiro algarismo",
        "algarismos iniciais",
        "digitos iniciais",
        "primeiros digitos",
        "distribuicao atipica dos primeiros",
        "padroes dos primeiros digitos",
    )
    if _contains_any(text, benford_paraphrases):
        return _decision(
            Route.METHODOLOGY,
            "pergunta metodológica sobre distribuição de dígitos",
            EvidenceLayer.METHODOLOGY,
            EvidenceLayer.KNOWLEDGE,
        )

    statistical_interpretation_cues = (
        "distribuicao numerica",
        "padrao esperado",
        "anomalia estatistica",
        "alerta estatistico",
        "sinal estatistico",
        "resultado isolado",
        "triagem",
        "validacao humana",
    )
    if _contains_any(text, statistical_interpretation_cues) and _contains_any(
        text,
        ("fraude", "investigacao", "diagnosticar", "conclusao", "validacao", "triagem"),
    ):
        return _decision(
            Route.METHODOLOGY,
            "pedido de interpretação cautelosa de sinal ou anomalia analítica",
            EvidenceLayer.METHODOLOGY,
        )

    scientific_method_topics = (
        "inteligencia de negocios",
        "business intelligence",
        "painel analitico",
        "paineis",
        "inteligencia artificial",
        "auditoria de recursos publicos",
        "fiscalizacao de gastos publicos",
        "gasto publico",
        "gastos publicos",
        "informacao publica",
        "compreender informacao publica",
        "portal da transparencia",
        "transparencia governamental",
        "controle social",
        "participacao no controle",
        "capacidade do cidadao",
        "competencia informacional",
        "competencia em informacao",
        "selecionar casos",
        "exame mais aprofundado",
        "triagem",
        "investigacao",
        "validacao humana",
        "analise forense",
        "analises forenses",
    )
    if _asks_scientific_sources(text) and _contains_any(text, scientific_method_topics):
        return _decision(
            Route.METHODOLOGY,
            "pedido de literatura científica sobre método, auditoria ou capacidade informacional",
            EvidenceLayer.METHODOLOGY,
        )

    overlap_cues = (
        "sobrepos",
        "quase os mesmos alertas",
        "alertas muito parecidos",
        "eliminar uma delas",
        "excluir uma trilha",
        "fundidas automaticamente",
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
        "e correto comparar",
        "anos fechados",
        "anos completos",
        "ano incompleto",
        "ano parcial",
        "ano ainda parcial",
        "ainda incompleto",
        "periodo parcial",
        "valores absolutos",
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
        ("pagamento duplicado", "duplicidade", "coincidencia exata", "valores identicos"),
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
    if _contains_any(text, territorial_terms) or _mentions_multiple_uf_codes(text):
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
        "qual e o fundamento",
        "qual fundamento",
        "que fundamento",
        "qual referencia normativa",
        "que referencia normativa",
        "que ato ",
        "quais atos ",
        "que manual ",
        "onde encontro orientacao",
        "existe publicacao",
        "que normas ",
        "quais normas ",
        "que decisao de controle externo",
        "qual deliberacao",
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
        "como reconstruir ",
        "preciso consultar ",
        "qual documento ",
        "o que consta ",
        "se eu precisar consultar ",
    )
    domain_terms = (
        "cpgf",
        "cartao de pagamento do governo federal",
        "cartao de pagamento do governo",
        "cartao corporativo federal",
        "cartao governamental",
        "cartao do governo",
        "suprimento de fundos",
        "suprimentos de fundos",
        "por suprimento",
        "agente suprido",
        "suprido",
        "ordenador de despesa",
        "prestacao de contas",
        "saque",
        "dinheiro em especie",
        "numerario",
        "adiantamento",
        "fracionamento",
        "material permanente",
        "cartilha",
        "portaria",
        "portarias",
        "acordao",
        "tribunal de contas da uniao",
        "tcu",
        "fiscalizacao continua",
        "controle externo",
        "parcelar uma aquisicao",
    )
    documentary_cues = (
        "referencia",
        "referencias",
        "fonte oficial",
        "fontes oficiais",
        "orientacao oficial",
        "orientacoes oficiais",
        "ato federal",
        "atos posteriores",
        "manual institucional",
        "norma geral",
        "normas",
        "fontes normativas",
        "fontes institucionais",
        "regulamentacao",
        "decisao de controle externo",
        "deliberacao",
        "pronunciamento",
        "precedente",
        "documento do corpus",
        "consultar",
    )
    public_spending_cues = (
        "despesa",
        "despesas",
        "aquisicao",
        "aquisicoes",
        "contratacao",
        "cartao",
        "suprimento",
        "suprido",
        "adiantamento",
        "numerario",
        "controle externo",
        "tcu",
        "acordao",
    )
    if text.startswith(conceptual_starts) or _contains_any(text, domain_terms):
        return _decision(
            Route.KNOWLEDGE,
            "pergunta conceitual/normativa sobre o domínio CPGF ou controle externo",
            EvidenceLayer.KNOWLEDGE,
        )
    if _contains_any(text, documentary_cues) and _contains_any(text, public_spending_cues):
        return _decision(
            Route.KNOWLEDGE,
            "pedido documental/normativo sobre despesa pública, CPGF ou controle externo",
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
