from __future__ import annotations

from hashlib import md5

import pandas as pd

from cpgf.preprocessing.schema import RAW_REQUIRED_COLUMNS

from .base import ensure_transaction_ids, keyed_signal_id_md5, require_columns

T03_MIN_OCCURRENCES = 2
T03_REINFORCED_OCCURRENCES = 3


def _eligible_t03(staged: pd.DataFrame, portador_column: str) -> pd.DataFrame:
    required = [
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
    ]
    require_columns(staged, required)

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
    eligible["_PORTADOR_T03"] = portador_key
    eligible["ID_TRANSACAO"] = ensure_transaction_ids(staged).loc[eligible.index]
    return eligible


def detect_exact_repetition_groups(
    staged: pd.DataFrame,
    *,
    portador_column: str = "PORTADOR_ID",
) -> pd.DataFrame:
    """Executa T03-A: repetição comportamental pela chave congelada."""
    eligible = _eligible_t03(staged, portador_column)
    key = [
        "UG_ID",
        "_PORTADOR_T03",
        "FAVORECIDO_ID",
        "DATA_DT",
        "TRANSAÇÃO",
        "VALOR_NUM",
        "VALOR_CENTAVOS",
    ]
    groups = (
        eligible.groupby(key, sort=False, dropna=False)
        .size()
        .rename("N_TRANSACOES")
        .reset_index()
    )
    groups = groups.loc[groups["N_TRANSACOES"] >= T03_MIN_OCCURRENCES].copy()
    groups = groups.rename(
        columns={
            "_PORTADOR_T03": "PORTADOR_ID",
            "TRANSAÇÃO": "TRANSACAO",
            "VALOR_NUM": "VALOR_UNITARIO",
        }
    )
    groups["VALOR_TOTAL_CENTAVOS"] = (
        groups["VALOR_CENTAVOS"].astype("Int64") * groups["N_TRANSACOES"].astype("Int64")
    )
    groups["NIVEL_TRIAGEM"] = groups["N_TRANSACOES"].ge(
        T03_REINFORCED_OCCURRENCES
    ).map({True: "REFORCADO", False: "ATENCAO"})

    if groups.empty:
        groups.insert(0, "ID_SINAL", pd.Series(index=groups.index, dtype="string"))
        return groups.reset_index(drop=True)

    def signal_id(row: pd.Series) -> str:
        return keyed_signal_id_md5(
            "T03",
            row["UG_ID"],
            row["PORTADOR_ID"],
            row["FAVORECIDO_ID"],
            pd.Timestamp(row["DATA_DT"]).date(),
            int(row["VALOR_CENTAVOS"]),
            row["TRANSACAO"],
        )

    groups.insert(0, "ID_SINAL", groups.apply(signal_id, axis=1))
    return groups.reset_index(drop=True)


def link_exact_repetition_transactions(
    staged: pd.DataFrame,
    groups: pd.DataFrame,
    *,
    portador_column: str = "PORTADOR_ID",
) -> pd.DataFrame:
    """Cria a ponte rastreável T03-A ↔ transações de origem."""
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

    eligible = _eligible_t03(staged, portador_column).rename(
        columns={"_PORTADOR_T03": "PORTADOR_ID", "TRANSAÇÃO": "TRANSACAO"}
    )
    key = ["UG_ID", "PORTADOR_ID", "FAVORECIDO_ID", "DATA_DT", "VALOR_CENTAVOS", "TRANSACAO"]
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


def detect_integral_observable_repetitions(staged: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Executa T03-B apenas como diagnóstico de repetição integral observável."""
    require_columns(
        staged,
        [
            *RAW_REQUIRED_COLUMNS,
            "UG_ID",
            "PORTADOR_ID",
            "FAVORECIDO_ID",
            "FAVORECIDO_IDENTIFICADO",
            "DATA_DT",
            "VALOR_NUM",
            "VALOR_CENTAVOS",
            "EH_COMPRA_EFETIVA",
            "EH_AJUSTE_CONTESTACAO",
            "EH_SIGILOSO",
        ],
    )
    mask = (
        staged["EH_COMPRA_EFETIVA"].fillna(False)
        & ~staged["EH_AJUSTE_CONTESTACAO"].fillna(False)
        & ~staged["EH_SIGILOSO"].fillna(False)
        & staged["VALOR_CENTAVOS"].gt(0).fillna(False)
        & staged["DATA_DT"].notna()
        & staged["UG_ID"].notna()
        & staged["PORTADOR_ID"].notna()
        & staged["FAVORECIDO_IDENTIFICADO"].fillna(False)
    )
    eligible = staged.loc[mask].copy()
    eligible["ID_TRANSACAO"] = ensure_transaction_ids(staged).loc[eligible.index]
    raw = eligible.loc[:, RAW_REQUIRED_COLUMNS].astype("string").fillna("")
    payload = raw.agg("|".join, axis=1)
    eligible["HASH_REGISTRO_NEGOCIO"] = payload.map(
        lambda value: md5(value.encode("utf-8")).hexdigest()
    )

    counts = eligible.groupby("HASH_REGISTRO_NEGOCIO", sort=False).size()
    repeated_hashes = counts[counts >= 2].rename("N_REPETICOES")
    if repeated_hashes.empty:
        return {"groups": pd.DataFrame(), "transactions": pd.DataFrame()}

    repeated = eligible[eligible["HASH_REGISTRO_NEGOCIO"].isin(repeated_hashes.index)].copy()
    first = repeated.groupby("HASH_REGISTRO_NEGOCIO", sort=False).first().reset_index()
    groups = first[
        [
            "HASH_REGISTRO_NEGOCIO",
            "ID_TRANSACAO",
            "UG_ID",
            "PORTADOR_ID",
            "FAVORECIDO_ID",
            "DATA_DT",
            "TRANSAÇÃO",
            "VALOR_NUM",
            "VALOR_CENTAVOS",
        ]
    ].rename(columns={"ID_TRANSACAO": "ID_TRANSACAO_EXEMPLO", "TRANSAÇÃO": "TRANSACAO"})
    groups = groups.merge(repeated_hashes, on="HASH_REGISTRO_NEGOCIO", how="left")

    repeated["ID_GRUPO_INTEGRAL"] = repeated["HASH_REGISTRO_NEGOCIO"].map(
        lambda value: keyed_signal_id_md5("T03B", value)
    )
    transactions = repeated[
        [
            "ID_GRUPO_INTEGRAL",
            "HASH_REGISTRO_NEGOCIO",
            "ID_TRANSACAO",
            "UG_ID",
            "PORTADOR_ID",
            "FAVORECIDO_ID",
            "DATA_DT",
            "TRANSAÇÃO",
            "VALOR_NUM",
            "VALOR_CENTAVOS",
        ]
    ].rename(columns={"TRANSAÇÃO": "TRANSACAO"})
    return {"groups": groups.reset_index(drop=True), "transactions": transactions.reset_index(drop=True)}


def summarize_t03(groups: pd.DataFrame) -> pd.DataFrame:
    if groups.empty:
        return pd.DataFrame(columns=["NIVEL_TRIAGEM", "N_GRUPOS", "TRANSACOES_ENVOLVIDAS", "VALOR_TOTAL"])
    summary = (
        groups.groupby("NIVEL_TRIAGEM", sort=True)
        .agg(
            N_GRUPOS=("ID_SINAL", "size"),
            TRANSACOES_ENVOLVIDAS=("N_TRANSACOES", "sum"),
            VALOR_TOTAL_CENTAVOS=("VALOR_TOTAL_CENTAVOS", "sum"),
        )
        .reset_index()
    )
    summary["VALOR_TOTAL"] = summary.pop("VALOR_TOTAL_CENTAVOS") / 100.0
    return summary


def run_t03(staged: pd.DataFrame) -> dict[str, pd.DataFrame]:
    groups = detect_exact_repetition_groups(staged)
    integral = detect_integral_observable_repetitions(staged)
    return {
        "groups": groups,
        "transactions": link_exact_repetition_transactions(staged, groups),
        "summary": summarize_t03(groups),
        "integral_groups": integral["groups"],
        "integral_transactions": integral["transactions"],
    }
