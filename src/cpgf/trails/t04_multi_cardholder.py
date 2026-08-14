from __future__ import annotations

import pandas as pd

from .base import ensure_transaction_ids, keyed_signal_id_md5, require_columns

T04_MIN_CARDHOLDERS = 2
T04_REINFORCED_CARDHOLDERS = 3
T04_VERY_HIGH_CARDHOLDERS = 5


def _eligible_t04(staged: pd.DataFrame, portador_column: str) -> pd.DataFrame:
    require_columns(
        staged,
        [
            "UG_ID",
            portador_column,
            "FAVORECIDO_ID",
            "FAVORECIDO_IDENTIFICADO",
            "DATA_DT",
            "VALOR_NUM",
            "VALOR_CENTAVOS",
            "TRANSAÇÃO",
            "EH_COMPRA_EFETIVA",
            "EH_AJUSTE_CONTESTACAO",
        ],
    )
    mask = (
        staged["EH_COMPRA_EFETIVA"].fillna(False)
        & ~staged["EH_AJUSTE_CONTESTACAO"].fillna(False)
        & staged["VALOR_CENTAVOS"].gt(0).fillna(False)
        & staged["DATA_DT"].notna()
        & staged["UG_ID"].notna()
        & staged[portador_column].notna()
        & staged["FAVORECIDO_IDENTIFICADO"].fillna(False)
    )
    eligible = staged.loc[mask].copy()
    portador_key = eligible[portador_column].astype("string")
    drop_columns = {portador_column}
    if "PORTADOR_ID" in eligible.columns:
        drop_columns.add("PORTADOR_ID")
    eligible = eligible.drop(columns=list(drop_columns), errors="ignore")
    eligible["_PORTADOR_T04"] = portador_key
    eligible["ID_TRANSACAO"] = ensure_transaction_ids(staged).loc[eligible.index]
    return eligible


def detect_multi_cardholder_groups(
    staged: pd.DataFrame,
    *,
    portador_column: str = "PORTADOR_ID",
) -> pd.DataFrame:
    """Executa T04 na unidade UG × fornecedor × data × valor."""
    eligible = _eligible_t04(staged, portador_column)
    key = ["UG_ID", "FAVORECIDO_ID", "DATA_DT", "VALOR_NUM", "VALOR_CENTAVOS"]
    groups = (
        eligible.groupby(key, sort=False, dropna=False)
        .agg(
            N_TRANSACOES=("VALOR_CENTAVOS", "size"),
            N_PORTADORES=("_PORTADOR_T04", "nunique"),
        )
        .reset_index()
    )
    groups = groups.loc[
        groups["N_TRANSACOES"].ge(2) & groups["N_PORTADORES"].ge(T04_MIN_CARDHOLDERS)
    ].copy()
    groups = groups.rename(columns={"VALOR_NUM": "VALOR_UNITARIO"})
    groups["VALOR_TOTAL_CENTAVOS"] = (
        groups["VALOR_CENTAVOS"].astype("Int64") * groups["N_TRANSACOES"].astype("Int64")
    )

    def triage(n_cardholders: object) -> str:
        n = int(n_cardholders)
        if n >= T04_VERY_HIGH_CARDHOLDERS:
            return "MUITO_ELEVADO"
        if n >= T04_REINFORCED_CARDHOLDERS:
            return "REFORCADO"
        return "ATENCAO"

    groups["NIVEL_TRIAGEM"] = groups["N_PORTADORES"].map(triage)

    def signal_id(row: pd.Series) -> str:
        return keyed_signal_id_md5(
            "T04",
            row["UG_ID"],
            row["FAVORECIDO_ID"],
            pd.Timestamp(row["DATA_DT"]).date(),
            int(row["VALOR_CENTAVOS"]),
        )

    groups.insert(0, "ID_SINAL", groups.apply(signal_id, axis=1))
    return groups.reset_index(drop=True)


def link_multi_cardholder_transactions(
    staged: pd.DataFrame,
    groups: pd.DataFrame,
    *,
    portador_column: str = "PORTADOR_ID",
) -> pd.DataFrame:
    """Cria ponte T04 ↔ transações que formam cada grupo."""
    if groups.empty:
        return pd.DataFrame(
            columns=[
                "ID_SINAL",
                "ID_TRANSACAO",
                "UG_ID",
                "PORTADOR_ID",
                "FAVORECIDO_ID",
                "DATA_DT",
                "VALOR_NUM",
                "VALOR_CENTAVOS",
                "TRANSACAO",
                "COMPETENCIA_ARQUIVO",
                "ARQUIVO_ORIGEM",
            ]
        )

    eligible = _eligible_t04(staged, portador_column).rename(
        columns={"_PORTADOR_T04": "PORTADOR_ID", "TRANSAÇÃO": "TRANSACAO"}
    )
    key = ["UG_ID", "FAVORECIDO_ID", "DATA_DT", "VALOR_CENTAVOS"]
    bridge = eligible.merge(groups[["ID_SINAL", *key]], on=key, how="inner", validate="many_to_one")
    columns = [
        "ID_SINAL",
        "ID_TRANSACAO",
        "UG_ID",
        "PORTADOR_ID",
        "FAVORECIDO_ID",
        "DATA_DT",
        "VALOR_NUM",
        "VALOR_CENTAVOS",
        "TRANSACAO",
    ]
    for optional in ("COMPETENCIA_ARQUIVO", "ARQUIVO_ORIGEM"):
        if optional in bridge.columns:
            columns.append(optional)
    return bridge[columns].reset_index(drop=True)


def summarize_t04(groups: pd.DataFrame) -> pd.DataFrame:
    if groups.empty:
        return pd.DataFrame(
            columns=[
                "NIVEL_TRIAGEM",
                "N_GRUPOS",
                "TRANSACOES_ENVOLVIDAS",
                "VALOR_TOTAL",
                "MAX_PORTADORES",
            ]
        )
    summary = (
        groups.groupby("NIVEL_TRIAGEM", sort=True)
        .agg(
            N_GRUPOS=("ID_SINAL", "size"),
            TRANSACOES_ENVOLVIDAS=("N_TRANSACOES", "sum"),
            VALOR_TOTAL_CENTAVOS=("VALOR_TOTAL_CENTAVOS", "sum"),
            MAX_PORTADORES=("N_PORTADORES", "max"),
        )
        .reset_index()
    )
    summary["VALOR_TOTAL"] = summary.pop("VALOR_TOTAL_CENTAVOS") / 100.0
    return summary


def run_t04(staged: pd.DataFrame) -> dict[str, pd.DataFrame]:
    groups = detect_multi_cardholder_groups(staged)
    return {
        "groups": groups,
        "transactions": link_multi_cardholder_transactions(staged, groups),
        "summary": summarize_t04(groups),
    }
