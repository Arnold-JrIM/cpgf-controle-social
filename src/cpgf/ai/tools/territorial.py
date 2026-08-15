from __future__ import annotations

from cpgf.ai.contracts import (
    TerritorialMetricArgs,
    TerritorialUGArgs,
    ToolName,
    ToolResult,
    dataframe_records,
)
from cpgf.ai.tools.common import serving_provenance
from cpgf.dashboard.data import DashboardDataContext
from cpgf.dashboard.territorial import geographic_uf_metric, territorial_ug_context

_GEO_WARNING = (
    "UF representa a localização cadastral da Unidade Gestora e não necessariamente o local "
    "físico da compra, saque ou operação."
)


def territorial_metric(
    context: DashboardDataContext,
    args: TerritorialMetricArgs,
) -> ToolResult:
    frame = geographic_uf_metric(
        context,
        reference=args.reference,
        year=args.year,
        metric=args.metric,
    )
    return ToolResult(
        tool=ToolName.TERRITORIAL_METRIC,
        records=dataframe_records(frame),
        summary={"ufs": int(frame["UF"].nunique()) if not frame.empty else 0},
        warnings=[_GEO_WARNING],
        provenance=serving_provenance(),
    )


def territorial_ugs(
    context: DashboardDataContext,
    args: TerritorialUGArgs,
) -> ToolResult:
    frame = territorial_ug_context(
        context,
        uf=args.uf,
        year=args.year,
        limit=args.limit,
    )
    return ToolResult(
        tool=ToolName.TERRITORIAL_UG_CONTEXT,
        records=dataframe_records(frame),
        summary={"returned": len(frame), "uf": args.uf, "year": args.year},
        warnings=[
            _GEO_WARNING,
            "O contexto UG-ano não deve ser interpretado automaticamente como decomposição de uma métrica EXTRATO.",
        ],
        provenance=serving_provenance(),
    )
