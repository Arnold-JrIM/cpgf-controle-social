from __future__ import annotations

from cpgf.ai.contracts import EmptyArgs, ToolName, ToolResult
from cpgf.ai.tools.common import serving_provenance
from cpgf.dashboard.data import TRAIL_LABELS
from cpgf.version import (
    APP_VERSION,
    GEO_VERSION,
    MOTOR_VERSION,
    PREPARATION_VERSION,
    RULES_VERSION,
    SERVING_VERSION,
)


def methodology(_context: object, _args: EmptyArgs) -> ToolResult:
    records = [
        {"code": code, "label": label, "role": "NUCLEO" if code <= "T07" else "CONTEXTO"}
        for code, label in TRAIL_LABELS.items()
    ]
    return ToolResult(
        tool=ToolName.METHODOLOGY,
        records=records,
        summary={
            "app_version": APP_VERSION,
            "preparation_version": PREPARATION_VERSION,
            "rules_version": RULES_VERSION,
            "motor_version": MOTOR_VERSION,
            "serving_version": SERVING_VERSION,
            "geo_version": GEO_VERSION,
            "complete_diagnostic_years": "2013-2025",
            "partial_period": "2026",
        },
        warnings=[
            "Sobreposição ou multicolinearidade não implicam exclusão automática de trilha.",
            "Sinal analítico não equivale a irregularidade confirmada.",
        ],
        provenance=serving_provenance(),
    )
