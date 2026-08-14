from __future__ import annotations

import pandas as pd

from .base import ensure_transaction_ids, keyed_signal_id_md5, require_columns

T07_MIN_WITHDRAWALS_DAY = 2
T07_REINFORCED_WITHDRAWALS_DAY = 3
T07_MIN_RECURRING_DAYS = 3
T07_PRIORITY_QUANTILE = 0.90
T07_MIN_YEAR_COMPARABLES = 10


def _eligible_withdrawals(staged: pd.DataFrame, portador_column: str) -> pd.DataFrame:
    require_columns(
        staged,
        [
            "UG_ID",
            portador_column,
            "DATA_DT",
            "ANO_TRANSACAO",
            "VALOR_CENTAVOS",
            "TRANSAÇÃO",
            "EH_SAQUE_EFETIVO",
        ],
    )
    mask = (
        staged["EH_SAQUE_EFETIVO"].fillna(False)
        & staged["DATA_DT"].notna()
        & staged["UG_ID"].notna()
        & staged[portador_column].notna()
        & staged["VALOR_CENTAVOS"].notna()
    )
    eligible = staged.loc[mask].copy()
    eligible["_PORTADOR_T07"] = eligible[portador_column].astype("string")
    eligible["ID_TRANSACAO"] = ensure_transaction_ids(staged).loc[eligible.index]
    return eligible


def detect_daily_multiwithdrawal_episodes(
    staged: pd.DataFrame,
    *,
    portador_column: str = "PORTADOR_ID",
) -> pd.DataFrame:
    """Executa T07-A: episódios com pelo menos dois saques no mesmo dia."""
    eligible = _eligible_withdrawals(staged, portador_column)
    if eligible.empty:
        return pd.DataFrame()

    key = ["UG_ID", "_PORTADOR_T07", "DATA_DT", "ANO_TRANSACAO"]
    daily = (
        eligible.groupby(key, sort=False, dropna=False)
        .agg(
            N_SAQUES=("VALOR_CENTAVOS", "size"),
            TOTAL_CENTAVOS=("VALOR_CENTAVOS", "sum"),
            MAIOR_SAQUE_CENTAVOS=("VALOR_CENTAVOS", "max"),
            TIPOS_SAQUE=("TRANSAÇÃO", lambda values: " | ".join(sorted(set(map(str, values))))),
        )
        .reset_index()
    )
    daily = daily.loc[daily["N_SAQUES"].ge(T07_MIN_WITHDRAWALS_DAY)].copy()
    daily = daily.rename(columns={"_PORTADOR_T07": "PORTADOR_ID"})
    if daily.empty:
        daily.insert(0, "ID_EPISODIO", pd.Series(dtype="string"))
        daily["NIVEL_EPISODIO"] = pd.Series(dtype="string")
        return daily

    daily["NIVEL_EPISODIO"] = daily["N_SAQUES"].ge(
        T07_REINFORCED_WITHDRAWALS_DAY
    ).map({True: "REFORCADO", False: "ATENCAO"})
    daily.insert(
        0,
        "ID_EPISODIO",
        daily.apply(
            lambda row: keyed_signal_id_md5(
                "T07D",
                row["UG_ID"],
                row["PORTADOR_ID"],
                pd.Timestamp(row["DATA_DT"]).date(),
            ),
            axis=1,
        ),
    )
    return daily.reset_index(drop=True)


def link_daily_multiwithdrawal_transactions(
    staged: pd.DataFrame,
    episodes: pd.DataFrame,
    *,
    portador_column: str = "PORTADOR_ID",
) -> pd.DataFrame:
    """Cria a ponte T07-A ↔ saques que compõem cada episódio diário."""
    if episodes.empty:
        return pd.DataFrame()

    eligible = _eligible_withdrawals(staged, portador_column).rename(
        columns={"_PORTADOR_T07": "PORTADOR_ID", "TRANSAÇÃO": "TRANSACAO"}
    )
    key = ["UG_ID", "PORTADOR_ID", "DATA_DT"]
    bridge = eligible.merge(
        episodes[["ID_EPISODIO", *key]],
        on=key,
        how="inner",
        validate="many_to_one",
    )
    columns = [
        "ID_EPISODIO",
        "ID_TRANSACAO",
        "UG_ID",
        "PORTADOR_ID",
        "DATA_DT",
        "ANO_TRANSACAO",
        "VALOR_NUM",
        "VALOR_CENTAVOS",
        "TRANSACAO",
    ]
    columns = [column for column in columns if column in bridge.columns]
    for optional in ("COMPETENCIA_ARQUIVO", "ARQUIVO_ORIGEM"):
        if optional in bridge.columns:
            columns.append(optional)
    return bridge[columns].reset_index(drop=True)


def compute_annual_withdrawal_recurrence(daily: pd.DataFrame) -> pd.DataFrame:
    """Resume episódios diários e calcula o P90 anual entre portadores comparáveis."""
    required = [
        "UG_ID",
        "PORTADOR_ID",
        "ANO_TRANSACAO",
        "DATA_DT",
        "N_SAQUES",
        "TOTAL_CENTAVOS",
    ]
    require_columns(daily, required)
    if daily.empty:
        return pd.DataFrame()

    annual = (
        daily.groupby(
            ["UG_ID", "PORTADOR_ID", "ANO_TRANSACAO"],
            sort=False,
            dropna=False,
        )
        .agg(
            N_DIAS_MULTISAQUE=("DATA_DT", "size"),
            TOTAL_SAQUES=("N_SAQUES", "sum"),
            TOTAL_VALOR_CENTAVOS=("TOTAL_CENTAVOS", "sum"),
            MAX_SAQUES_DIA=("N_SAQUES", "max"),
            MEDIA_SAQUES_DIA=("N_SAQUES", "mean"),
            PRIMEIRA_DATA=("DATA_DT", "min"),
            ULTIMA_DATA=("DATA_DT", "max"),
        )
        .reset_index()
    )

    year_stats = (
        annual.groupby("ANO_TRANSACAO", sort=False)["N_DIAS_MULTISAQUE"]
        .agg(
            N_PORTADORES_COMPARAVEIS_ANO="size",
            LIMIAR_PRIORIZACAO_DIAS=lambda values: values.quantile(
                T07_PRIORITY_QUANTILE, interpolation="linear"
            ),
        )
        .reset_index()
    )
    annual = annual.merge(year_stats, on="ANO_TRANSACAO", how="left", validate="many_to_one")

    def percent_rank(values: pd.Series) -> pd.Series:
        if len(values) <= 1:
            return pd.Series(0.0, index=values.index)
        return (values.rank(method="min") - 1) / (len(values) - 1)

    annual["PERCENT_RANK_DIAS"] = annual.groupby("ANO_TRANSACAO", group_keys=False)[
        "N_DIAS_MULTISAQUE"
    ].transform(percent_rank)
    annual["PRIORITARIO"] = (
        annual["N_DIAS_MULTISAQUE"].ge(T07_MIN_RECURRING_DAYS)
        & annual["N_PORTADORES_COMPARAVEIS_ANO"].ge(T07_MIN_YEAR_COMPARABLES)
        & annual["N_DIAS_MULTISAQUE"].ge(annual["LIMIAR_PRIORIZACAO_DIAS"])
    )
    return annual.reset_index(drop=True)


def detect_withdrawal_recurrence_signals(
    staged: pd.DataFrame,
    *,
    portador_column: str = "PORTADOR_ID",
) -> pd.DataFrame:
    """Executa T07-B e retorna somente portador-anos priorizados."""
    daily = detect_daily_multiwithdrawal_episodes(staged, portador_column=portador_column)
    annual = compute_annual_withdrawal_recurrence(daily)
    if annual.empty:
        return annual

    signals = annual.loc[annual["PRIORITARIO"]].copy()
    if signals.empty:
        signals.insert(0, "ID_SINAL", pd.Series(dtype="string"))
        return signals
    signals.insert(
        0,
        "ID_SINAL",
        signals.apply(
            lambda row: keyed_signal_id_md5(
                "T07",
                row["UG_ID"],
                row["PORTADOR_ID"],
                int(row["ANO_TRANSACAO"]),
            ),
            axis=1,
        ),
    )
    return signals.reset_index(drop=True)


def link_priority_withdrawal_transactions(
    staged: pd.DataFrame,
    signals: pd.DataFrame,
    *,
    portador_column: str = "PORTADOR_ID",
) -> pd.DataFrame:
    """Liga T07-B aos saques efetivos do portador no respectivo exercício."""
    if signals.empty:
        return pd.DataFrame()

    eligible = _eligible_withdrawals(staged, portador_column).rename(
        columns={"_PORTADOR_T07": "PORTADOR_ID", "TRANSAÇÃO": "TRANSACAO"}
    )
    keys = ["UG_ID", "PORTADOR_ID", "ANO_TRANSACAO"]
    bridge = eligible.merge(
        signals[["ID_SINAL", *keys]],
        on=keys,
        how="inner",
        validate="many_to_one",
    )
    columns = [
        "ID_SINAL",
        "ID_TRANSACAO",
        "UG_ID",
        "PORTADOR_ID",
        "ANO_TRANSACAO",
        "DATA_DT",
        "VALOR_NUM",
        "VALOR_CENTAVOS",
        "TRANSACAO",
    ]
    columns = [column for column in columns if column in bridge.columns]
    for optional in ("COMPETENCIA_ARQUIVO", "ARQUIVO_ORIGEM"):
        if optional in bridge.columns:
            columns.append(optional)
    return bridge[columns].reset_index(drop=True)


def run_t07(
    staged: pd.DataFrame,
    *,
    portador_column: str = "PORTADOR_ID",
) -> dict[str, pd.DataFrame]:
    daily = detect_daily_multiwithdrawal_episodes(staged, portador_column=portador_column)
    annual = compute_annual_withdrawal_recurrence(daily)
    signals = annual.loc[annual["PRIORITARIO"]].copy() if not annual.empty else annual.copy()
    if not signals.empty:
        signals.insert(
            0,
            "ID_SINAL",
            signals.apply(
                lambda row: keyed_signal_id_md5(
                    "T07",
                    row["UG_ID"],
                    row["PORTADOR_ID"],
                    int(row["ANO_TRANSACAO"]),
                ),
                axis=1,
            ),
        )
    elif "ID_SINAL" not in signals.columns:
        signals.insert(0, "ID_SINAL", pd.Series(dtype="string"))
    return {
        "daily_episodes": daily,
        "daily_transactions": link_daily_multiwithdrawal_transactions(
            staged, daily, portador_column=portador_column
        ),
        "annual": annual,
        "signals": signals.reset_index(drop=True),
        "priority_transactions": link_priority_withdrawal_transactions(
            staged, signals, portador_column=portador_column
        ),
    }
