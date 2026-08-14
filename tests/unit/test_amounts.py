import pandas as pd

from cpgf.preprocessing.amounts import parse_amount_series_to_cents, parse_brl_to_cents


def test_parse_brl_to_cents_official_format():
    assert parse_brl_to_cents("1.234,56") == 123456
    assert parse_brl_to_cents("R$ 10,05") == 1005
    assert parse_brl_to_cents("-10,05") == -1005


def test_parse_brl_to_cents_missing_or_invalid():
    assert parse_brl_to_cents("") is None
    assert parse_brl_to_cents(None) is None
    assert parse_brl_to_cents("abc") is None


def test_amount_series_uses_nullable_integer():
    result = parse_amount_series_to_cents(pd.Series(["10,00", "", "-0,01"]))
    assert result.iloc[0] == 1000
    assert pd.isna(result.iloc[1])
    assert result.iloc[2] == -1
    assert str(result.dtype) == "Int64"
