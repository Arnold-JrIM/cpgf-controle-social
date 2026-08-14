from __future__ import annotations

from typing import Any

import pandas as pd

COMPRA_NACIONAL = "COMPRA A/V - R$ - APRES"
COMPRA_INTERNACIONAL = "COMPRA A/V - INT$ - APRES"
COMPRA_PARCELADA = "CPP LOJISTA TRF P/FATURA - REAL"

COMPRAS_EFETIVAS = frozenset({COMPRA_NACIONAL, COMPRA_INTERNACIONAL, COMPRA_PARCELADA})
SAQUES_EFETIVOS = frozenset(
    {
        "SAQUE CASH/ATM BB",
        "SAQUE - INT$ - APRES",
        "SAQUE MANUAL - CARTOES BB NA AGENCIA",
        "SAQUE - R$ - APRES",
    }
)
AJUSTES_CONTESTACAO = frozenset(
    {
        "COMP A/V-SOL DISP C/CLI-R$ ANT VENC",
        "COMP A/V-SOL DISP C/CLI-R$ APOS VENC",
        "SAQUE BB B24HORAS-SOL C/CLIENTE",
        "VOUCHER - R$ - REVRS REAPR",
    }
)


def _code(value: Any) -> str:
    return "" if value is None else str(value).strip()


def is_compra_efetiva(value: Any) -> bool:
    return _code(value) in COMPRAS_EFETIVAS


def is_compra_nacional(value: Any) -> bool:
    return _code(value) == COMPRA_NACIONAL


def is_saque_efetivo(value: Any) -> bool:
    return _code(value) in SAQUES_EFETIVOS


def is_ajuste_contestacao(value: Any) -> bool:
    return _code(value) in AJUSTES_CONTESTACAO


def transaction_flags(series: pd.Series) -> pd.DataFrame:
    codes = series.astype("string").fillna("").str.strip()
    return pd.DataFrame(
        {
            "EH_COMPRA_EFETIVA": codes.isin(COMPRAS_EFETIVAS),
            "EH_COMPRA_NACIONAL": codes.eq(COMPRA_NACIONAL),
            "EH_SAQUE_EFETIVO": codes.isin(SAQUES_EFETIVOS),
            "EH_AJUSTE_CONTESTACAO": codes.isin(AJUSTES_CONTESTACAO),
        },
        index=series.index,
    )


def sigilo_flags(
    transaction: pd.Series,
    portador_name: pd.Series,
    favorecido_name: pd.Series,
) -> pd.Series:
    """Marca presença explícita do termo sigilo nos campos observáveis."""
    def contains_sigilo(series: pd.Series) -> pd.Series:
        return series.astype("string").fillna("").str.contains("sigilo", case=False, regex=False)

    return contains_sigilo(transaction) | contains_sigilo(portador_name) | contains_sigilo(favorecido_name)
