from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


COMPLETE_YEAR_START = 2013
COMPLETE_YEAR_END = 2025
BASELINE_COMPLETE_SUPPLIER_YEAR_N = 522_053
BASELINE_COMPLETE_UG_YEAR_N = 13_785


@dataclass(frozen=True)
class SupplierExposureBand:
    order: int
    code: str
    label: str
    minimum: int
    maximum: int | None


SUPPLIER_EXPOSURE_BANDS: tuple[SupplierExposureBand, ...] = (
    SupplierExposureBand(1, "B01_1", "1 compra", 1, 1),
    SupplierExposureBand(2, "B02_2", "2 compras", 2, 2),
    SupplierExposureBand(3, "B03_3_4", "3-4 compras", 3, 4),
    SupplierExposureBand(4, "B04_5_9", "5-9 compras", 5, 9),
    SupplierExposureBand(5, "B05_10_19", "10-19 compras", 10, 19),
    SupplierExposureBand(6, "B06_20_MAIS", "20+ compras", 20, None),
)


SUPPLIER_YEAR_REQUIRED_COLUMNS: tuple[str, ...] = (
    "UG_ID",
    "FAVORECIDO_ID",
    "FAVORECIDO_IDENTIFICADO",
    "PORTADOR_ID",
    "DATA_DT",
    "ANO_TRANSACAO",
    "VALOR_CENTAVOS",
    "EH_COMPRA_EFETIVA",
    "EH_AJUSTE_CONTESTACAO",
)

UG_YEAR_REQUIRED_COLUMNS: tuple[str, ...] = (
    "UG_ID",
    "FAVORECIDO_ID",
    "FAVORECIDO_IDENTIFICADO",
    "PORTADOR_ID",
    "DATA_DT",
    "ANO_TRANSACAO",
    "VALOR_CENTAVOS",
    "EH_COMPRA_EFETIVA",
    "EH_SAQUE_EFETIVO",
    "EH_AJUSTE_CONTESTACAO",
)


def _require_columns(frame: pd.DataFrame, columns: tuple[str, ...]) -> None:
    missing = [column for column in columns if column not in frame.columns]
    if missing:
        raise ValueError(f"Colunas ausentes para governança de exposição: {missing}")


def _boolean_series(frame: pd.DataFrame, column: str) -> pd.Series:
    return frame[column].fillna(False).astype(bool)


def period_status_series(years: pd.Series) -> pd.Series:
    numeric_year = pd.to_numeric(years, errors="coerce")
    complete = numeric_year.between(COMPLETE_YEAR_START, COMPLETE_YEAR_END)
    return pd.Series(
        np.where(complete, "COMPLETO", "PARCIAL"),
        index=years.index,
        dtype="string",
    )


def complete_period_mask(frame: pd.DataFrame, year_column: str = "ANO") -> pd.Series:
    if year_column not in frame.columns:
        raise ValueError(f"Coluna de ano ausente: {year_column}")
    years = pd.to_numeric(frame[year_column], errors="coerce")
    return years.between(COMPLETE_YEAR_START, COMPLETE_YEAR_END).fillna(False)


def add_supplier_exposure_bands(
    frame: pd.DataFrame,
    exposure_column: str = "N_COMPRAS_FORNECEDOR",
) -> pd.DataFrame:
    """Aplica as seis bandas fixas congeladas para UG × fornecedor × ano."""
    if exposure_column not in frame.columns:
        raise ValueError(f"Coluna de exposição ausente: {exposure_column}")

    result = frame.copy()
    exposure = pd.to_numeric(result[exposure_column], errors="coerce")
    invalid = exposure.isna() | exposure.lt(1)
    if invalid.any():
        examples = result.loc[invalid, exposure_column].head(5).tolist()
        raise ValueError(
            "N_COMPRAS_FORNECEDOR deve ser inteiro positivo para todas as unidades; "
            f"exemplos inválidos: {examples}"
        )

    codes = pd.Series(pd.NA, index=result.index, dtype="string")
    labels = pd.Series(pd.NA, index=result.index, dtype="string")
    orders = pd.Series(pd.NA, index=result.index, dtype="Int64")

    for band in SUPPLIER_EXPOSURE_BANDS:
        if band.maximum is None:
            mask = exposure.ge(band.minimum)
        else:
            mask = exposure.between(band.minimum, band.maximum)
        codes.loc[mask] = band.code
        labels.loc[mask] = band.label
        orders.loc[mask] = band.order

    if codes.isna().any():
        raise AssertionError(
            "Exposição fornecedor: existem unidades elegíveis sem banda de exposição."
        )

    result["BANDA_EXPOSICAO_FORNECEDOR"] = codes
    result["ROTULO_BANDA_EXPOSICAO_FORNECEDOR"] = labels
    result["ORDEM_BANDA_EXPOSICAO_FORNECEDOR"] = orders
    return result


def add_ug_annual_exposure_deciles(
    frame: pd.DataFrame,
    exposure_column: str = "N_OPERACOES_EFETIVAS",
    year_column: str = "ANO",
    n_deciles: int = 10,
) -> pd.DataFrame:
    """Calcula decis anuais preservando empates por rank médio percentual."""
    if exposure_column not in frame.columns:
        raise ValueError(f"Coluna de exposição ausente: {exposure_column}")
    if year_column not in frame.columns:
        raise ValueError(f"Coluna de ano ausente: {year_column}")
    if n_deciles < 1:
        raise ValueError("n_deciles deve ser positivo.")

    result = frame.copy()
    exposure = pd.to_numeric(result[exposure_column], errors="coerce")
    years = pd.to_numeric(result[year_column], errors="coerce")
    invalid = exposure.isna() | exposure.lt(1) | years.isna()
    if invalid.any():
        raise ValueError(
            "Exposição anual da UG exige ano válido e N_OPERACOES_EFETIVAS positivo."
        )

    rank_frame = pd.DataFrame(
        {"ANO": years, "EXPOSICAO": exposure},
        index=result.index,
    )
    percentile = rank_frame.groupby("ANO")["EXPOSICAO"].rank(
        method="average",
        pct=True,
    )
    decile = np.ceil(percentile * n_deciles).clip(1, n_deciles)

    result["PERCENTIL_EXPOSICAO_ANUAL"] = percentile.astype("Float64")
    result["DECIL_EXPOSICAO_ANUAL"] = pd.Series(
        decile,
        index=result.index,
    ).astype("Int64")
    return result


def build_supplier_year_universe(
    staged: pd.DataFrame,
    *,
    complete_years_only: bool = False,
) -> pd.DataFrame:
    """Constrói o universo diagnóstico UG × fornecedor × ano do Motor 1.3.2."""
    _require_columns(staged, SUPPLIER_YEAR_REQUIRED_COLUMNS)

    value_cents = pd.to_numeric(staged["VALOR_CENTAVOS"], errors="coerce")
    eligible = (
        _boolean_series(staged, "EH_COMPRA_EFETIVA")
        & ~_boolean_series(staged, "EH_AJUSTE_CONTESTACAO")
        & value_cents.gt(0).fillna(False)
        & staged["DATA_DT"].notna()
        & staged["UG_ID"].notna()
        & _boolean_series(staged, "FAVORECIDO_IDENTIFICADO")
        & staged["ANO_TRANSACAO"].notna()
    )

    work = staged.loc[
        eligible,
        [
            "UG_ID",
            "FAVORECIDO_ID",
            "PORTADOR_ID",
            "DATA_DT",
            "ANO_TRANSACAO",
            "VALOR_CENTAVOS",
        ],
    ].copy()
    work["VALOR_CENTAVOS"] = pd.to_numeric(work["VALOR_CENTAVOS"], errors="raise")
    work["ANO_TRANSACAO"] = pd.to_numeric(
        work["ANO_TRANSACAO"], errors="raise"
    ).astype("Int64")

    universe = (
        work.groupby(
            ["UG_ID", "FAVORECIDO_ID", "ANO_TRANSACAO"],
            dropna=False,
            sort=True,
        )
        .agg(
            N_COMPRAS_FORNECEDOR=("VALOR_CENTAVOS", "size"),
            VALOR_COMPRAS_FORNECEDOR=("VALOR_CENTAVOS", "sum"),
            N_PORTADORES_FORNECEDOR=("PORTADOR_ID", "nunique"),
            N_DIAS_COMPRA_FORNECEDOR=("DATA_DT", "nunique"),
        )
        .reset_index()
        .rename(
            columns={
                "UG_ID": "CODIGO_UG",
                "FAVORECIDO_ID": "CHAVE_ENTIDADE",
                "ANO_TRANSACAO": "ANO",
            }
        )
    )
    universe["VALOR_COMPRAS_FORNECEDOR"] = (
        universe["VALOR_COMPRAS_FORNECEDOR"] / 100.0
    )
    universe["N_COMPRAS_FORNECEDOR"] = universe["N_COMPRAS_FORNECEDOR"].astype(
        "Int64"
    )
    universe["N_PORTADORES_FORNECEDOR"] = universe[
        "N_PORTADORES_FORNECEDOR"
    ].astype("Int64")
    universe["N_DIAS_COMPRA_FORNECEDOR"] = universe[
        "N_DIAS_COMPRA_FORNECEDOR"
    ].astype("Int64")
    universe["STATUS_PERIODO"] = period_status_series(universe["ANO"])
    universe = add_supplier_exposure_bands(universe)

    if complete_years_only:
        universe = universe.loc[complete_period_mask(universe)].copy()

    return universe.sort_values(
        ["ANO", "CODIGO_UG", "CHAVE_ENTIDADE"],
        kind="stable",
    ).reset_index(drop=True)


def build_ug_year_universe(
    staged: pd.DataFrame,
    *,
    complete_years_only: bool = False,
) -> pd.DataFrame:
    """Constrói o universo diagnóstico UG × ano e seus decis anuais de exposição."""
    _require_columns(staged, UG_YEAR_REQUIRED_COLUMNS)

    purchases = _boolean_series(staged, "EH_COMPRA_EFETIVA")
    withdrawals = _boolean_series(staged, "EH_SAQUE_EFETIVO")
    adjustments = _boolean_series(staged, "EH_AJUSTE_CONTESTACAO")
    value_cents = pd.to_numeric(staged["VALOR_CENTAVOS"], errors="coerce")

    eligible = (
        staged["DATA_DT"].notna()
        & staged["UG_ID"].notna()
        & staged["ANO_TRANSACAO"].notna()
        & ~adjustments
        & value_cents.gt(0).fillna(False)
        & (purchases | withdrawals)
    )

    work = staged.loc[
        eligible,
        [
            "UG_ID",
            "FAVORECIDO_ID",
            "PORTADOR_ID",
            "DATA_DT",
            "ANO_TRANSACAO",
            "VALOR_CENTAVOS",
            "EH_COMPRA_EFETIVA",
            "EH_SAQUE_EFETIVO",
            "FAVORECIDO_IDENTIFICADO",
        ],
    ].copy()
    work["VALOR_CENTAVOS"] = pd.to_numeric(work["VALOR_CENTAVOS"], errors="raise")
    work["ANO_TRANSACAO"] = pd.to_numeric(
        work["ANO_TRANSACAO"], errors="raise"
    ).astype("Int64")
    work["EH_COMPRA_EFETIVA"] = work["EH_COMPRA_EFETIVA"].fillna(False).astype(bool)
    work["EH_SAQUE_EFETIVO"] = work["EH_SAQUE_EFETIVO"].fillna(False).astype(bool)
    work["FAVORECIDO_IDENTIFICADO"] = (
        work["FAVORECIDO_IDENTIFICADO"].fillna(False).astype(bool)
    )

    work["VALOR_COMPRA_CENTAVOS"] = work["VALOR_CENTAVOS"].where(
        work["EH_COMPRA_EFETIVA"], 0
    )
    work["VALOR_SAQUE_CENTAVOS"] = work["VALOR_CENTAVOS"].where(
        work["EH_SAQUE_EFETIVO"], 0
    )
    work["FAVORECIDO_COMPRA"] = work["FAVORECIDO_ID"].where(
        work["EH_COMPRA_EFETIVA"] & work["FAVORECIDO_IDENTIFICADO"]
    )

    universe = (
        work.groupby(["UG_ID", "ANO_TRANSACAO"], dropna=False, sort=True)
        .agg(
            N_COMPRAS_UG=("EH_COMPRA_EFETIVA", "sum"),
            VALOR_COMPRAS_UG=("VALOR_COMPRA_CENTAVOS", "sum"),
            N_SAQUES_UG=("EH_SAQUE_EFETIVO", "sum"),
            VALOR_SAQUES_UG=("VALOR_SAQUE_CENTAVOS", "sum"),
            N_OPERACOES_EFETIVAS=("VALOR_CENTAVOS", "size"),
            N_PORTADORES_UG=("PORTADOR_ID", "nunique"),
            N_FORNECEDORES_UG=("FAVORECIDO_COMPRA", "nunique"),
            N_DIAS_ATIVOS_UG=("DATA_DT", "nunique"),
        )
        .reset_index()
        .rename(columns={"UG_ID": "CODIGO_UG", "ANO_TRANSACAO": "ANO"})
    )

    for column in (
        "N_COMPRAS_UG",
        "N_SAQUES_UG",
        "N_OPERACOES_EFETIVAS",
        "N_PORTADORES_UG",
        "N_FORNECEDORES_UG",
        "N_DIAS_ATIVOS_UG",
    ):
        universe[column] = universe[column].astype("Int64")

    universe["VALOR_COMPRAS_UG"] = universe["VALOR_COMPRAS_UG"] / 100.0
    universe["VALOR_SAQUES_UG"] = universe["VALOR_SAQUES_UG"] / 100.0
    universe["STATUS_PERIODO"] = period_status_series(universe["ANO"])
    universe = add_ug_annual_exposure_deciles(universe)

    if complete_years_only:
        universe = universe.loc[complete_period_mask(universe)].copy()

    return universe.sort_values(
        ["ANO", "CODIGO_UG"],
        kind="stable",
    ).reset_index(drop=True)
