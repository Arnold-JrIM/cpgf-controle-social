from __future__ import annotations

import math


def format_integer(value: int | float | None) -> str:
    if value is None:
        return "—"
    return f"{int(value):,}".replace(",", ".")


def format_currency(value: int | float | None) -> str:
    if value is None:
        return "—"
    numeric = float(value)
    if not math.isfinite(numeric):
        return "—"
    if abs(numeric) >= 1_000_000_000:
        return f"R$ {numeric / 1_000_000_000:.2f} bi".replace(".", ",")
    if abs(numeric) >= 1_000_000:
        return f"R$ {numeric / 1_000_000:.2f} mi".replace(".", ",")
    return f"R$ {numeric:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def format_percent(value: int | float | None, digits: int = 1) -> str:
    if value is None:
        return "—"
    return f"{float(value) * 100:.{digits}f}%".replace(".", ",")


def format_geographic_metric(
    value: int | float | None,
    unit: str,
    *,
    digits: int = 1,
) -> str:
    """Formata unidades do Geo 1.1.0; percentuais já chegam na escala 0–100."""
    if value is None:
        return "—"
    numeric = float(value)
    if not math.isfinite(numeric):
        return "—"
    normalized = str(unit).strip().upper()
    if normalized == "BRL":
        return format_currency(numeric)
    if normalized == "PERCENTUAL":
        return f"{numeric:.{digits}f}%".replace(".", ",")
    if normalized == "CONTAGEM":
        return format_integer(numeric)
    return f"{numeric:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
