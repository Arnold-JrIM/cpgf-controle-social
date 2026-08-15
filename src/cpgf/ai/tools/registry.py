from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from pydantic import BaseModel

from cpgf.ai.contracts import (
    EmptyArgs,
    QueryScope,
    RankingArgs,
    TerritorialMetricArgs,
    TerritorialUGArgs,
    ToolName,
    ToolRequest,
    ToolResult,
)
from cpgf.ai.tools.methodology import methodology
from cpgf.ai.tools.signals import overview, ranked_suppliers, ranked_ugs, trails
from cpgf.ai.tools.territorial import territorial_metric, territorial_ugs
from cpgf.dashboard.data import DashboardDataContext

Handler = Callable[[DashboardDataContext, BaseModel], ToolResult]


@dataclass(frozen=True)
class ToolSpec:
    arguments_model: type[BaseModel]
    handler: Handler
    description: str


TOOL_REGISTRY: dict[ToolName, ToolSpec] = {
    ToolName.OVERVIEW: ToolSpec(QueryScope, overview, "Resumo agregado por período e UGs."),
    ToolName.TRAIL_PREVALENCE: ToolSpec(
        QueryScope, trails, "Prevalência T01–T09 nas unidades UG-ano."
    ),
    ToolName.TOP_UGS: ToolSpec(RankingArgs, ranked_ugs, "UGs priorizadas por recorrência."),
    ToolName.TOP_SUPPLIERS: ToolSpec(
        RankingArgs, ranked_suppliers, "Fornecedores priorizados por recorrência."
    ),
    ToolName.TERRITORIAL_METRIC: ToolSpec(
        TerritorialMetricArgs,
        territorial_metric,
        "Métrica UF×ano já materializada pela Geo 1.1.0.",
    ),
    ToolName.TERRITORIAL_UG_CONTEXT: ToolSpec(
        TerritorialUGArgs,
        territorial_ugs,
        "Contexto das UGs de uma UF em um ano.",
    ),
    ToolName.METHODOLOGY: ToolSpec(
        EmptyArgs, methodology, "Versões, papéis das trilhas e salvaguardas."
    ),
}


def tool_catalog() -> list[dict[str, str]]:
    return [
        {"name": name.value, "description": spec.description}
        for name, spec in TOOL_REGISTRY.items()
    ]


def execute_tool(context: DashboardDataContext, request: ToolRequest) -> ToolResult:
    """Despacha somente ferramentas registradas; argumentos extras são rejeitados por Pydantic."""
    spec = TOOL_REGISTRY[request.tool]
    arguments = spec.arguments_model.model_validate(request.arguments)
    return spec.handler(context, arguments)
