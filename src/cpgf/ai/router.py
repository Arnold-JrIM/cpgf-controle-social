from __future__ import annotations

import re
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
    UNSUPPORTED = "unsupported"


class RouteDecision(BaseModel):
    model_config = ConfigDict(frozen=True)
    route: Route
    reason: str
    deterministic: bool = True


_PATTERNS: tuple[tuple[Route, re.Pattern[str], str], ...] = (
    (Route.METHODOLOGY, re.compile(r"\b(metodologia|método|vers(ão|oes|ões)|como funciona)\b", re.I), "termos metodológicos"),
    (Route.TERRITORIAL, re.compile(r"\b(UF|estado|territ(ório|orial)|mapa|regi(ão|oes|ões))\b", re.I), "termos territoriais"),
    (Route.SUPPLIERS, re.compile(r"\b(fornecedor(es)?|favorecido(s)?)\b", re.I), "termos de fornecedor"),
    (Route.UGS, re.compile(r"\b(UG|unidade(s)? gestora(s)?)\b", re.I), "termos de Unidade Gestora"),
    (Route.TRAILS, re.compile(r"\b(T0[1-9]|trilha(s)?|sinal(is)?|alerta(s)?)\b", re.I), "termos de trilhas/sinais"),
    (Route.OVERVIEW, re.compile(r"\b(gasto(s)?|despesa(s)?|valor(es)?|operaç(ão|oes|ões)|resumo|vis(ão|ao) geral)\b", re.I), "termos de visão geral"),
)


def route_question(question: str) -> RouteDecision:
    """Roteamento lexical conservador; não substitui interpretação semântica futura do LLM."""
    text = validate_question(question)
    for route, pattern, reason in _PATTERNS:
        if pattern.search(text):
            return RouteDecision(route=route, reason=reason)
    return RouteDecision(
        route=Route.UNSUPPORTED,
        reason="nenhum domínio analítico autorizado foi identificado de forma determinística",
    )
