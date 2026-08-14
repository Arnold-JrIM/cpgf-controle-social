from __future__ import annotations

from decimal import ROUND_HALF_EVEN, Decimal, InvalidOperation
from typing import Any

import pandas as pd

_MISSING_TEXT = {"", "NAN", "NA", "N/A", "NULL", "NONE", "<NA>"}
_CENT = Decimal("0.01")
_HUNDRED = Decimal("100")


def parse_brl_amount(value: Any) -> Decimal | None:
    """Converte valor monetário observável em ``Decimal`` com duas casas.

    O formato oficial esperado usa vírgula decimal. Formatos já normalizados
    com ponto decimal também são aceitos. Valores ausentes ou não numéricos
    retornam ``None``; nenhuma imputação é realizada.
    """
    if value is None:
        return None

    raw = str(value).strip().replace("\u00a0", " ")
    if raw.upper() in _MISSING_TEXT:
        return None

    raw = raw.replace("R$", "").replace(" ", "")
    negative_parentheses = raw.startswith("(") and raw.endswith(")")
    if negative_parentheses:
        raw = raw[1:-1]

    if "," in raw:
        raw = raw.replace(".", "").replace(",", ".")

    try:
        amount = Decimal(raw)
    except InvalidOperation:
        return None

    if negative_parentheses:
        amount = -amount
    return amount.quantize(_CENT, rounding=ROUND_HALF_EVEN)


def parse_brl_to_cents(value: Any) -> int | None:
    """Converte valor monetário para centavos inteiros."""
    amount = parse_brl_amount(value)
    if amount is None:
        return None
    return int((amount * _HUNDRED).to_integral_value(rounding=ROUND_HALF_EVEN))


def parse_amount_series_to_cents(series: pd.Series) -> pd.Series:
    """Versão vetorial com dtype anulável ``Int64``."""
    parsed = series.map(parse_brl_to_cents)
    return pd.Series(parsed, index=series.index, dtype="Int64")


def cents_to_reais_series(series: pd.Series) -> pd.Series:
    """Representação analítica em reais; comparações exatas devem usar centavos."""
    numeric = pd.to_numeric(series, errors="coerce").astype("Float64")
    return numeric / 100.0
