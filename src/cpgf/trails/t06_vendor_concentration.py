from __future__ import annotations

import pandas as pd

from .base import ensure_transaction_ids, keyed_signal_id_md5, require_columns

T06_MIN_IDENTIFIED_PURCHASES = 20
T06_MIN_VENDORS = 3
T06_MIN_IDENTIFIED_VALUE_COVERAGE = 0.80
T06_SHARE_BASE = 0.50
T06_SHARE_REINFORCED = 0.70
T06_SHARE_VERY_HIGH = 0.80


def _eligible_national_purchases(staged: pd.DataFrame) -> pd.DataFrame:
    require_columns(
        staged,
        [
            "UG_ID",
            "ANO_TRANSACAO",
            "FAVORECIDO_ID",
            "FAVORECIDO_IDENTIFICADO",
            "VALOR_CENTAVOS",
            "EH_COMPRA_NACIONAL",
        ],
    )
    mask = (
        staged["EH_COMPRA_NACIONAL"].fillna(False)
        & staged["VALOR_CENTAVOS"].gt(0).fillna(False)
        & staged["UG_ID"].notna()
        & staged["ANO_TRANSACAO"].notna()
    )
    return staged.loc[mask].copy()


def compute_concentration_indicators(staged: pd.DataFrame) -> pd.DataFrame:
    """Calcula os indicadores estruturais congelados de T06 por UG × ano."""
    base = _eligible_national_purchases(staged)
    if base.empty:
        return pd.DataFrame()

    total = (
        base.groupby(["UG_ID", "ANO_TRANSACAO"], sort=False, dropna=False)
        .agg(
            N_TOTAL_COMPRAS=("VALOR_CENTAVOS", "size"),
            TOTAL_UG_CENTAVOS=("VALOR_CENTAVOS", "sum"),
        )
        .reset_index()
    )

    identified = base.loc[base["FAVORECIDO_IDENTIFICADO"].fillna(False)].copy()
    if identified.empty:
        output = total.copy()
        for column in (
            "N_FORNECEDORES",
            "N_COMPRAS_IDENTIFICADAS",
            "TOTAL_IDENTIFICADO_CENTAVOS",
            "TOP1_FAVORECIDO_ID",
            "TOP1_VALOR_CENTAVOS",
            "TOP1_SHARE_VALOR",
            "TOP1_SHARE_QTD",
            "TOP5_SHARE_VALOR",
            "HHI",
            "TOP1_FAVORECIDO_QTD",
            "TOP1_QTD_TRANSACOES",
            "TOP1_SHARE_QTD_MAX",
            "COBERTURA_VALOR_IDENTIFICADO",
        ):
            output[column] = pd.NA
        return output

    supplier = (
        identified.groupby(
            ["UG_ID", "ANO_TRANSACAO", "FAVORECIDO_ID"],
            sort=False,
            dropna=False,
        )
        .agg(
            N_FORN=("VALOR_CENTAVOS", "size"),
            V_FORN_CENTAVOS=("VALOR_CENTAVOS", "sum"),
        )
        .reset_index()
    )

    keys = ["UG_ID", "ANO_TRANSACAO"]
    supplier["TOTAL_IDENTIFICADO_CENTAVOS"] = supplier.groupby(keys)[
        "V_FORN_CENTAVOS"
    ].transform("sum")
    supplier["N_COMPRAS_IDENTIFICADAS"] = supplier.groupby(keys)["N_FORN"].transform(
        "sum"
    )
    supplier["N_FORNECEDORES"] = supplier.groupby(keys)["FAVORECIDO_ID"].transform(
        "size"
    )
    supplier["SHARE"] = (
        supplier["V_FORN_CENTAVOS"] / supplier["TOTAL_IDENTIFICADO_CENTAVOS"]
    )
    supplier["SHARE_QTD"] = supplier["N_FORN"] / supplier["N_COMPRAS_IDENTIFICADAS"]

    value_ranked = supplier.sort_values(
        ["UG_ID", "ANO_TRANSACAO", "V_FORN_CENTAVOS", "FAVORECIDO_ID"],
        ascending=[True, True, False, True],
        kind="mergesort",
    ).copy()
    value_ranked["RN_VALOR"] = value_ranked.groupby(keys, sort=False).cumcount().add(1)

    first = value_ranked.loc[value_ranked["RN_VALOR"].eq(1)].copy()
    first = first[
        [
            *keys,
            "N_FORNECEDORES",
            "N_COMPRAS_IDENTIFICADAS",
            "TOTAL_IDENTIFICADO_CENTAVOS",
            "FAVORECIDO_ID",
            "V_FORN_CENTAVOS",
            "SHARE",
            "SHARE_QTD",
        ]
    ].rename(
        columns={
            "FAVORECIDO_ID": "TOP1_FAVORECIDO_ID",
            "V_FORN_CENTAVOS": "TOP1_VALOR_CENTAVOS",
            "SHARE": "TOP1_SHARE_VALOR",
            "SHARE_QTD": "TOP1_SHARE_QTD",
        }
    )

    top5 = (
        value_ranked.loc[value_ranked["RN_VALOR"].le(5)]
        .groupby(keys, sort=False)["SHARE"]
        .sum()
        .rename("TOP5_SHARE_VALOR")
        .reset_index()
    )
    hhi = (
        supplier.assign(_SHARE2=supplier["SHARE"].pow(2))
        .groupby(keys, sort=False)["_SHARE2"]
        .sum()
        .rename("HHI")
        .reset_index()
    )

    quantity_ranked = supplier.sort_values(
        ["UG_ID", "ANO_TRANSACAO", "N_FORN", "FAVORECIDO_ID"],
        ascending=[True, True, False, True],
        kind="mergesort",
    )
    quantity_top = quantity_ranked.groupby(keys, sort=False).head(1)[
        [*keys, "FAVORECIDO_ID", "N_FORN", "SHARE_QTD"]
    ].rename(
        columns={
            "FAVORECIDO_ID": "TOP1_FAVORECIDO_QTD",
            "N_FORN": "TOP1_QTD_TRANSACOES",
            "SHARE_QTD": "TOP1_SHARE_QTD_MAX",
        }
    )

    indicators = first.merge(top5, on=keys, how="left", validate="one_to_one")
    indicators = indicators.merge(hhi, on=keys, how="left", validate="one_to_one")
    indicators = indicators.merge(quantity_top, on=keys, how="left", validate="one_to_one")
    indicators = total.merge(indicators, on=keys, how="left", validate="one_to_one")
    indicators["COBERTURA_VALOR_IDENTIFICADO"] = (
        indicators["TOTAL_IDENTIFICADO_CENTAVOS"] / indicators["TOTAL_UG_CENTAVOS"]
    )
    return indicators.reset_index(drop=True)


def detect_vendor_concentration_signals(staged: pd.DataFrame) -> pd.DataFrame:
    """Prioriza UG-anos com concentração Top-1 conforme os limiares congelados."""
    indicators = compute_concentration_indicators(staged)
    if indicators.empty:
        return indicators

    mask = (
        indicators["N_COMPRAS_IDENTIFICADAS"].ge(T06_MIN_IDENTIFIED_PURCHASES).fillna(False)
        & indicators["N_FORNECEDORES"].ge(T06_MIN_VENDORS).fillna(False)
        & indicators["COBERTURA_VALOR_IDENTIFICADO"]
        .ge(T06_MIN_IDENTIFIED_VALUE_COVERAGE)
        .fillna(False)
        & indicators["TOP1_SHARE_VALOR"].ge(T06_SHARE_BASE).fillna(False)
    )
    signals = indicators.loc[mask].copy()
    if signals.empty:
        signals.insert(0, "ID_SINAL", pd.Series(dtype="string"))
        signals["NIVEL_TRIAGEM"] = pd.Series(dtype="string")
        return signals

    def triage(value: object) -> str:
        share = float(value)
        if share >= T06_SHARE_VERY_HIGH:
            return "MUITO_ELEVADO"
        if share >= T06_SHARE_REINFORCED:
            return "REFORCADO"
        return "ATENCAO"

    signals["NIVEL_TRIAGEM"] = signals["TOP1_SHARE_VALOR"].map(triage)
    signals.insert(
        0,
        "ID_SINAL",
        signals.apply(
            lambda row: keyed_signal_id_md5(
                "T06", row["UG_ID"], int(row["ANO_TRANSACAO"])
            ),
            axis=1,
        ),
    )
    return signals.reset_index(drop=True)


def link_concentration_top1_transactions(
    staged: pd.DataFrame, signals: pd.DataFrame
) -> pd.DataFrame:
    """Liga cada sinal T06 às compras nacionais do fornecedor Top-1 por valor."""
    if signals.empty:
        return pd.DataFrame()

    base = _eligible_national_purchases(staged)
    base["ID_TRANSACAO"] = ensure_transaction_ids(staged).loc[base.index]
    keys = ["UG_ID", "ANO_TRANSACAO"]
    bridge = base.merge(
        signals[["ID_SINAL", *keys, "TOP1_FAVORECIDO_ID"]],
        on=keys,
        how="inner",
        validate="many_to_one",
    )
    bridge = bridge.loc[bridge["FAVORECIDO_ID"].eq(bridge["TOP1_FAVORECIDO_ID"])].copy()
    columns = [
        "ID_SINAL",
        "ID_TRANSACAO",
        "UG_ID",
        "ANO_TRANSACAO",
        "FAVORECIDO_ID",
        "DATA_DT",
        "VALOR_NUM",
        "VALOR_CENTAVOS",
    ]
    columns = [column for column in columns if column in bridge.columns]
    for optional in ("COMPETENCIA_ARQUIVO", "ARQUIVO_ORIGEM"):
        if optional in bridge.columns:
            columns.append(optional)
    return bridge[columns].reset_index(drop=True)


def run_t06(staged: pd.DataFrame) -> dict[str, pd.DataFrame]:
    indicators = compute_concentration_indicators(staged)
    signals = detect_vendor_concentration_signals(staged)
    return {
        "indicators": indicators,
        "signals": signals,
        "transactions": link_concentration_top1_transactions(staged, signals),
    }
