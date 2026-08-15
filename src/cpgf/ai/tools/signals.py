from __future__ import annotations

from cpgf.ai.contracts import QueryScope, RankingArgs, ToolName, ToolResult, dataframe_records
from cpgf.ai.tools.common import serving_provenance
from cpgf.dashboard.data import (
    DashboardDataContext,
    DashboardFilter,
    overview_summary,
    top_suppliers,
    top_ugs,
    trail_prevalence,
)


def _filters(args: QueryScope) -> DashboardFilter:
    return DashboardFilter(
        year_start=args.year_start,
        year_end=args.year_end,
        ug_codes=args.ug_codes,
    )


def overview(context: DashboardDataContext, args: QueryScope) -> ToolResult:
    summary = overview_summary(context, _filters(args))
    return ToolResult(
        tool=ToolName.OVERVIEW,
        summary=summary,
        provenance=serving_provenance(),
    )


def trails(context: DashboardDataContext, args: QueryScope) -> ToolResult:
    frame = trail_prevalence(context, _filters(args))
    return ToolResult(
        tool=ToolName.TRAIL_PREVALENCE,
        records=dataframe_records(frame),
        summary={"units": int(frame["N_UNIVERSO"].max()) if not frame.empty else 0},
        warnings=[
            "T08 e T09 são contexto e não integram o núcleo de convergência T01–T07."
        ],
        provenance=serving_provenance(),
    )


def ranked_ugs(context: DashboardDataContext, args: RankingArgs) -> ToolResult:
    frame = top_ugs(context, _filters(args), limit=args.limit)
    return ToolResult(
        tool=ToolName.TOP_UGS,
        records=dataframe_records(frame),
        summary={"returned": len(frame)},
        warnings=[
            "Recorrência de sinais é critério de priorização analítica, não confirmação de irregularidade."
        ],
        provenance=serving_provenance(),
    )


def ranked_suppliers(context: DashboardDataContext, args: RankingArgs) -> ToolResult:
    frame = top_suppliers(context, _filters(args), limit=args.limit)
    return ToolResult(
        tool=ToolName.TOP_SUPPLIERS,
        records=dataframe_records(frame),
        summary={"returned": len(frame)},
        warnings=[
            "A presença recorrente de um fornecedor em sinais não comprova favorecimento ou fraude."
        ],
        provenance=serving_provenance(),
    )
