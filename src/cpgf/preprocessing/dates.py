from __future__ import annotations

from typing import Any

import pandas as pd

TRANSACTION_DATE_FORMAT = "%d/%m/%Y"


def parse_transaction_date(value: Any) -> pd.Timestamp | pd.NaT:
    """Converte exclusivamente a data observável da transação."""
    if value is None or str(value).strip() == "":
        return pd.NaT
    return pd.to_datetime(str(value).strip(), format=TRANSACTION_DATE_FORMAT, errors="coerce")


def parse_transaction_dates(series: pd.Series) -> pd.Series:
    cleaned = series.astype("string").str.strip().replace("", pd.NA)
    return pd.to_datetime(cleaned, format=TRANSACTION_DATE_FORMAT, errors="coerce")


def transaction_year(dates: pd.Series) -> pd.Series:
    return dates.dt.year.astype("Int64")


def parse_extract_year(series: pd.Series) -> pd.Series:
    values = pd.to_numeric(series.astype("string").str.strip(), errors="coerce").astype("Int64")
    return values.mask((values < 2000) | (values > 2100))


def parse_extract_month(series: pd.Series) -> pd.Series:
    values = pd.to_numeric(series.astype("string").str.strip(), errors="coerce").astype("Int64")
    return values.mask((values < 1) | (values > 12))


def build_extract_competence(year: pd.Series, month: pd.Series) -> pd.Series:
    """Monta ``YYYYMM`` da referência de extrato sem substituir DATA TRANSAÇÃO."""
    valid = year.notna() & month.notna()
    result = pd.Series(pd.NA, index=year.index, dtype="string")
    result.loc[valid] = (
        year.loc[valid].astype(int).astype(str) + month.loc[valid].astype(int).astype(str).str.zfill(2)
    )
    return result
