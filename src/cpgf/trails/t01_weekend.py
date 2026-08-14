from __future__ import annotations

import pandas as pd

from .base import (
    build_signal_ids,
    ensure_transaction_ids,
    optional_series,
    period_status,
    require_columns,
)

_WEEKDAY_LABELS = {
    0: "segunda-feira",
    1: "terça-feira",
    2: "quarta-feira",
    3: "quinta-feira",
    4: "sexta-feira",
    5: "sábado",
    6: "domingo",
}


def detect_weekend_purchases(staged: pd.DataFrame) -> pd.DataFrame:
    """Executa T01 no nível transação conforme Regras 1.2.0."""
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
            "EH_COMPRA_EFETIVA",
            "EH_AJUSTE_CONTESTACAO",
        ],
    )

    transaction_ids = ensure_transaction_ids(staged)
    weekday = staged["DATA_DT"].dt.dayofweek
    mask = (
        staged["EH_COMPRA_EFETIVA"].fillna(False)
        & ~staged["EH_AJUSTE_CONTESTACAO"].fillna(False)
        & staged["DATA_DT"].notna()
        & weekday.isin([5, 6])
    )

    selected = staged.loc[mask].copy()
    selected_ids = transaction_ids.loc[mask]
    selected_weekday = weekday.loc[mask]

    result = pd.DataFrame(index=selected.index)
    result["ID_SINAL"] = build_signal_ids("T01", selected_ids)
    result["ID_TRANSACAO"] = selected_ids.astype("string")
    result["UG_ID"] = selected["UG_ID"]
    result["NOME_UG"] = optional_series(selected, "NOME UNIDADE GESTORA")
    result["PORTADOR_ID"] = selected["PORTADOR_ID"]
    result["NOME_PORTADOR"] = optional_series(selected, "NOME PORTADOR")
    result["FAVORECIDO_ID"] = selected["FAVORECIDO_ID"]
    result["NOME_FAVORECIDO"] = optional_series(selected, "NOME FAVORECIDO")
    result["DATA_DT"] = selected["DATA_DT"]
    result["DIA_SEMANA_TXT"] = selected_weekday.map(_WEEKDAY_LABELS).astype("string")
    result["VALOR_NUM"] = selected["VALOR_NUM"]
    result["VALOR_CENTAVOS"] = selected["VALOR_CENTAVOS"]
    result["TRANSACAO"] = selected["TRANSAÇÃO"]
    result["COMPETENCIA_ARQUIVO"] = optional_series(selected, "COMPETENCIA_ARQUIVO")
    result["ARQUIVO_ORIGEM"] = optional_series(selected, "ARQUIVO_ORIGEM")
    result["NIVEL_TRIAGEM"] = "ATENCAO"
    result["EVIDENCIA"] = (
        "Compra realizada em final de semana; verificar justificativa documental."
    )
    result["LIMITACAO"] = "A base pública não contém a justificativa da despesa."
    return result.reset_index(drop=True)


def build_weekend_recurrence(
    staged: pd.DataFrame,
    *,
    portador_column: str = "PORTADOR_ID",
) -> pd.DataFrame:
    """Calcula o contexto descritivo anual de T01 sem criar novo sinal."""
    require_columns(
        staged,
        [
            "UG_ID",
            portador_column,
            "ANO_TRANSACAO",
            "DATA_DT",
            "VALOR_CENTAVOS",
            "EH_COMPRA_NACIONAL",
        ],
    )

    eligible = staged.loc[
        staged["EH_COMPRA_NACIONAL"].fillna(False)
        & staged["DATA_DT"].notna()
        & staged["UG_ID"].notna()
        & staged[portador_column].notna()
    ].copy()

    if eligible.empty:
        return pd.DataFrame(
            columns=[
                "UG_ID",
                "PORTADOR_ID",
                "ANO_TRANSACAO",
                "N_COMPRAS",
                "N_FIM_SEMANA",
                "N_DIAS_FIM_SEMANA",
                "VALOR_FIM_SEMANA_CENTAVOS",
                "SHARE_FIM_SEMANA",
                "PERCENT_RANK_N_FIM_SEMANA",
            ]
        )

    eligible["_PORTADOR"] = eligible[portador_column].astype("string")
    eligible["_EH_FIM_SEMANA"] = eligible["DATA_DT"].dt.dayofweek.isin([5, 6])
    eligible["_DATA_FIM_SEMANA"] = eligible["DATA_DT"].where(
        eligible["_EH_FIM_SEMANA"]
    )
    eligible["_VALOR_FIM_SEMANA"] = eligible["VALOR_CENTAVOS"].where(
        eligible["_EH_FIM_SEMANA"], 0
    )

    grouped = (
        eligible.groupby(["UG_ID", "_PORTADOR", "ANO_TRANSACAO"], dropna=False)
        .agg(
            N_COMPRAS=("DATA_DT", "size"),
            N_FIM_SEMANA=("_EH_FIM_SEMANA", "sum"),
            N_DIAS_FIM_SEMANA=("_DATA_FIM_SEMANA", "nunique"),
            VALOR_FIM_SEMANA_CENTAVOS=("_VALOR_FIM_SEMANA", "sum"),
        )
        .reset_index()
        .rename(columns={"_PORTADOR": "PORTADOR_ID"})
    )
    grouped = grouped.loc[grouped["N_FIM_SEMANA"] > 0].copy()
    grouped["SHARE_FIM_SEMANA"] = grouped["N_FIM_SEMANA"] / grouped["N_COMPRAS"]

    def percent_rank(values: pd.Series) -> pd.Series:
        if len(values) <= 1:
            return pd.Series(0.0, index=values.index)
        rank = values.rank(method="min")
        return (rank - 1) / (len(values) - 1)

    grouped["PERCENT_RANK_N_FIM_SEMANA"] = grouped.groupby(
        "ANO_TRANSACAO", group_keys=False
    )["N_FIM_SEMANA"].transform(percent_rank)
    return grouped.reset_index(drop=True)


def summarize_weekend_signals(signals: pd.DataFrame) -> pd.DataFrame:
    """Resumo anual compatível com a baseline T01."""
    if signals.empty:
        return pd.DataFrame(columns=["ANO", "N_SINAIS", "VALOR_TOTAL", "STATUS_PERIODO"])

    result = (
        signals.assign(ANO=signals["DATA_DT"].dt.year.astype("Int64"))
        .groupby("ANO", dropna=False)
        .agg(N_SINAIS=("ID_SINAL", "size"), VALOR_TOTAL=("VALOR_NUM", "sum"))
        .reset_index()
        .sort_values("ANO")
    )
    result["STATUS_PERIODO"] = result["ANO"].map(period_status)
    return result.reset_index(drop=True)


def summarize_weekend_recurrence(recurrence: pd.DataFrame) -> pd.DataFrame:
    """Resumo anual do contexto de recorrência T01."""
    if recurrence.empty:
        return pd.DataFrame(
            columns=[
                "ANO_TRANSACAO",
                "N_PORTADORES_COM_FIM_SEMANA",
                "MEDIANA_OCORRENCIAS",
                "MAX_OCORRENCIAS",
                "SHARE_MEDIO",
                "STATUS_PERIODO",
            ]
        )

    result = (
        recurrence.groupby("ANO_TRANSACAO", dropna=False)
        .agg(
            N_PORTADORES_COM_FIM_SEMANA=("PORTADOR_ID", "size"),
            MEDIANA_OCORRENCIAS=("N_FIM_SEMANA", "median"),
            MAX_OCORRENCIAS=("N_FIM_SEMANA", "max"),
            SHARE_MEDIO=("SHARE_FIM_SEMANA", "mean"),
        )
        .reset_index()
        .sort_values("ANO_TRANSACAO")
    )
    result["STATUS_PERIODO"] = result["ANO_TRANSACAO"].map(period_status)
    return result.reset_index(drop=True)


def run_t01(staged: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Executa sinal, contexto e resumos de T01."""
    signals = detect_weekend_purchases(staged)
    recurrence = build_weekend_recurrence(staged)
    return {
        "signals": signals,
        "recurrence": recurrence,
        "annual_summary": summarize_weekend_signals(signals),
        "recurrence_annual_summary": summarize_weekend_recurrence(recurrence),
    }
