import pandas as pd

from cpgf.preprocessing.dates import (
    build_extract_competence,
    parse_extract_month,
    parse_extract_year,
    parse_transaction_dates,
    transaction_year,
)


def test_transaction_date_is_independent_from_extract_reference():
    dates = parse_transaction_dates(pd.Series(["05/01/2025", "", "31/02/2025"]))
    years = transaction_year(dates)
    assert str(dates.iloc[0].date()) == "2025-01-05"
    assert pd.isna(dates.iloc[1])
    assert pd.isna(dates.iloc[2])
    assert years.iloc[0] == 2025


def test_extract_competence_is_separate_field():
    year = parse_extract_year(pd.Series(["2025", "2025", "x"]))
    month = parse_extract_month(pd.Series(["01", "13", "02"]))
    competence = build_extract_competence(year, month)
    assert competence.iloc[0] == "202501"
    assert pd.isna(competence.iloc[1])
    assert pd.isna(competence.iloc[2])
