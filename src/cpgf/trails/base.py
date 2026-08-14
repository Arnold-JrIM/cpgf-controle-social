from __future__ import annotations

from hashlib import md5
from typing import Iterable

import pandas as pd

from cpgf.version import RULES_VERSION


def require_columns(frame: pd.DataFrame, columns: Iterable[str]) -> None:
    """Valida as colunas mínimas exigidas por uma trilha."""
    missing = [column for column in columns if column not in frame.columns]
    if missing:
        raise ValueError(f"Colunas ausentes para execução da trilha: {missing}")


def optional_series(frame: pd.DataFrame, column: str, dtype: str = "string") -> pd.Series:
    """Retorna uma coluna existente ou uma série anulável alinhada ao índice."""
    if column in frame.columns:
        return frame[column]
    return pd.Series(pd.NA, index=frame.index, dtype=dtype)


def ensure_transaction_ids(frame: pd.DataFrame) -> pd.Series:
    """Obtém ``ID_TRANSACAO`` ou o reconstrói pelo contrato histórico.

    Na baseline consolidada, o identificador é ``COMPETENCIA_ARQUIVO`` + posição
    original dentro de ``ARQUIVO_ORIGEM``. A reconstrução pressupõe que a ordem
    do staging preserve a ordem do arquivo de origem.
    """
    if "ID_TRANSACAO" in frame.columns and frame["ID_TRANSACAO"].notna().all():
        return frame["ID_TRANSACAO"].astype("string")

    if "COMPETENCIA_ARQUIVO" not in frame.columns:
        raise ValueError(
            "ID_TRANSACAO ausente e COMPETENCIA_ARQUIVO indisponível para reconstrução."
        )

    if "ARQUIVO_ORIGEM" in frame.columns:
        group_key = frame["ARQUIVO_ORIGEM"].astype("string").fillna("")
    else:
        group_key = frame["COMPETENCIA_ARQUIVO"].astype("string").fillna("")

    sequence = frame.groupby(group_key, sort=False, dropna=False).cumcount().add(1)
    prefix = frame["COMPETENCIA_ARQUIVO"].astype("string").fillna("")
    generated = prefix + ":" + sequence.astype("string").str.zfill(8)

    if "ID_TRANSACAO" not in frame.columns:
        return generated

    current = frame["ID_TRANSACAO"].astype("string")
    return current.where(current.notna() & current.ne(""), generated)


def build_signal_ids(code: str, transaction_ids: pd.Series) -> pd.Series:
    """Reproduz o identificador determinístico usado na baseline congelada."""

    def signal_id(transaction_id: object) -> str:
        payload = f"{code}|{RULES_VERSION}|{transaction_id}"
        return f"{code}_{md5(payload.encode('utf-8')).hexdigest()}"

    return transaction_ids.astype("string").map(signal_id).astype("string")


def period_status(year: object) -> str:
    """Classifica a cobertura temporal da baseline atual."""
    try:
        numeric_year = int(year)
    except (TypeError, ValueError):
        return "PERIODO_INDEFINIDO"
    return "EXERCICIO_COMPLETO" if 2013 <= numeric_year <= 2025 else "PERIODO_PARCIAL"
