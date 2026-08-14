from __future__ import annotations

import pandas as pd

from cpgf.preprocessing.transaction_types import COMPRA_PARCELADA

from .base import build_signal_ids, ensure_transaction_ids, optional_series, require_columns


def detect_installment_transactions(staged: pd.DataFrame) -> pd.DataFrame:
    """Executa T02 por correspondência exata do código operacional congelado."""
    require_columns(
        staged,
        [
            "UG_ID",
            "PORTADOR_ID",
            "FAVORECIDO_ID",
            "DATA_DT",
            "VALOR_NUM",
            "VALOR_CENTAVOS",
            "TRANSAÇÃO",
        ],
    )

    transaction_ids = ensure_transaction_ids(staged)
    mask = staged["TRANSAÇÃO"].astype("string").fillna("").eq(COMPRA_PARCELADA)

    selected = staged.loc[mask].copy()
    selected_ids = transaction_ids.loc[mask]

    result = pd.DataFrame(index=selected.index)
    result["ID_SINAL"] = build_signal_ids("T02", selected_ids)
    result["ID_TRANSACAO"] = selected_ids.astype("string")
    result["UG_ID"] = selected["UG_ID"]
    result["NOME_UG"] = optional_series(selected, "NOME UNIDADE GESTORA")
    result["PORTADOR_ID"] = selected["PORTADOR_ID"]
    result["NOME_PORTADOR"] = optional_series(selected, "NOME PORTADOR")
    result["FAVORECIDO_ID"] = selected["FAVORECIDO_ID"]
    result["NOME_FAVORECIDO"] = optional_series(selected, "NOME FAVORECIDO")
    result["DATA_DT"] = selected["DATA_DT"]
    result["VALOR_NUM"] = selected["VALOR_NUM"]
    result["VALOR_CENTAVOS"] = selected["VALOR_CENTAVOS"]
    result["TRANSACAO"] = selected["TRANSAÇÃO"]
    result["COMPETENCIA_ARQUIVO"] = optional_series(selected, "COMPETENCIA_ARQUIVO")
    result["ARQUIVO_ORIGEM"] = optional_series(selected, "ARQUIVO_ORIGEM")
    result["NIVEL_TRIAGEM"] = "ATENCAO"
    result["EVIDENCIA"] = "Código operacional classificado como compra parcelada."
    result["LIMITACAO"] = (
        "A classificação deve ser conferida com a fatura e os documentos da despesa."
    )
    return result.reset_index(drop=True)


def summarize_installment_transactions(signals: pd.DataFrame) -> pd.DataFrame:
    """Resumo da T02 compatível com a baseline congelada."""
    if signals.empty:
        return pd.DataFrame(
            {
                "N_SINAIS": [0],
                "VALOR_TOTAL": [0.0],
                "PRIMEIRA_DATA": [pd.NaT],
                "ULTIMA_DATA": [pd.NaT],
            }
        )

    return pd.DataFrame(
        {
            "N_SINAIS": [len(signals)],
            "VALOR_TOTAL": [signals["VALOR_NUM"].fillna(0).sum()],
            "PRIMEIRA_DATA": [signals["DATA_DT"].min()],
            "ULTIMA_DATA": [signals["DATA_DT"].max()],
        }
    )


def run_t02(staged: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Executa sinal e resumo de T02."""
    signals = detect_installment_transactions(staged)
    return {
        "signals": signals,
        "summary": summarize_installment_transactions(signals),
    }
