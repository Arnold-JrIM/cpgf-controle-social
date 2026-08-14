import pandas as pd

from cpgf.preprocessing.identity_gate import normalize_digits, normalize_name


def test_normalize_digits_keeps_only_observed_digits():
    series = pd.Series(["***.123.***-**", " -1 ", ""])
    result = normalize_digits(series)
    assert result.iloc[0] == "123"
    assert result.iloc[1] == "1"
    assert pd.isna(result.iloc[2])


def test_normalize_name_removes_accents_case_and_extra_spaces():
    series = pd.Series(["  João   da Silva  "])
    result = normalize_name(series)
    assert result.iloc[0] == "JOAO DA SILVA"
