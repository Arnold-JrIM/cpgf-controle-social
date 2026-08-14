import pandas as pd

from cpgf.preprocessing.transaction_types import (
    AJUSTES_CONTESTACAO,
    COMPRA_NACIONAL,
    COMPRAS_EFETIVAS,
    SAQUES_EFETIVOS,
    sigilo_flags,
    transaction_flags,
)
from cpgf.settings.loader import load_yaml


def test_frozen_transaction_codebook_matches_config():
    cfg = load_yaml("transaction_codes.yaml")["transaction_codes"]
    expected_purchases = {
        cfg["compra_nacional"],
        cfg["compra_internacional"],
        cfg["compra_parcelada"],
    }
    assert COMPRAS_EFETIVAS == expected_purchases
    assert SAQUES_EFETIVOS == set(cfg["saques_efetivos"])
    assert AJUSTES_CONTESTACAO == set(cfg["ajustes_contestacao"])


def test_transaction_flags_are_exact_code_matches():
    series = pd.Series([COMPRA_NACIONAL, next(iter(SAQUES_EFETIVOS)), "CODIGO DESCONHECIDO"])
    flags = transaction_flags(series)
    assert flags.loc[0, "EH_COMPRA_EFETIVA"]
    assert flags.loc[0, "EH_COMPRA_NACIONAL"]
    assert flags.loc[1, "EH_SAQUE_EFETIVO"]
    assert not flags.loc[2, "EH_COMPRA_EFETIVA"]
    assert not flags.loc[2, "EH_SAQUE_EFETIVO"]


def test_sigilo_flag_uses_observable_text_fields():
    result = sigilo_flags(
        pd.Series(["COMPRA", "COMPRA"]),
        pd.Series(["Pessoa", "Informação protegida por sigilo"]),
        pd.Series(["Fornecedor", "Fornecedor"]),
    )
    assert result.tolist() == [False, True]
