from hashlib import md5

import pandas as pd

from cpgf.preprocessing.transaction_types import (
    COMPRA_INTERNACIONAL,
    COMPRA_NACIONAL,
    COMPRA_PARCELADA,
)
from cpgf.trails.t01_weekend import build_weekend_recurrence, detect_weekend_purchases
from cpgf.trails.t02_installment import detect_installment_transactions
from cpgf.version import RULES_VERSION


def _staged_fixture() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "COMPETENCIA_ARQUIVO": ["202501"] * 5,
            "ARQUIVO_ORIGEM": ["202501_CPGF.csv"] * 5,
            "UG_ID": ["000133"] * 5,
            "NOME UNIDADE GESTORA": ["UG TESTE"] * 5,
            "PORTADOR_ID": ["000133|123|PORTADOR TESTE"] * 5,
            "NOME PORTADOR": ["PORTADOR TESTE"] * 5,
            "FAVORECIDO_ID": ["12345678000199"] * 5,
            "NOME FAVORECIDO": ["FORNECEDOR TESTE"] * 5,
            "DATA_DT": pd.to_datetime(
                ["2025-01-04", "2025-01-05", "2025-01-06", "2025-01-11", "2025-01-12"]
            ),
            "ANO_TRANSACAO": pd.Series([2025] * 5, dtype="Int64"),
            "VALOR_NUM": pd.Series([10.0, 20.0, 30.0, 40.0, 50.0], dtype="Float64"),
            "VALOR_CENTAVOS": pd.Series([1000, 2000, 3000, 4000, 5000], dtype="Int64"),
            "TRANSAÇÃO": [
                COMPRA_NACIONAL,
                COMPRA_INTERNACIONAL,
                COMPRA_NACIONAL,
                COMPRA_PARCELADA,
                f"{COMPRA_PARCELADA} ",
            ],
            "EH_COMPRA_EFETIVA": [True, True, True, True, False],
            "EH_COMPRA_NACIONAL": [True, False, True, False, False],
            "EH_AJUSTE_CONTESTACAO": [False] * 5,
        }
    )


def test_t01_detects_only_effective_weekend_purchases():
    signals = detect_weekend_purchases(_staged_fixture())

    assert len(signals) == 3
    assert signals["DIA_SEMANA_TXT"].tolist() == ["sábado", "domingo", "sábado"]
    assert signals["NIVEL_TRIAGEM"].eq("ATENCAO").all()
    assert signals["ID_TRANSACAO"].tolist() == [
        "202501:00000001",
        "202501:00000002",
        "202501:00000004",
    ]

    expected_payload = f"T01|{RULES_VERSION}|202501:00000001"
    expected_id = f"T01_{md5(expected_payload.encode('utf-8')).hexdigest()}"
    assert signals.loc[0, "ID_SINAL"] == expected_id


def test_t01_recurrence_uses_only_national_purchases():
    recurrence = build_weekend_recurrence(_staged_fixture())

    assert len(recurrence) == 1
    row = recurrence.iloc[0]
    assert row["N_COMPRAS"] == 2
    assert row["N_FIM_SEMANA"] == 1
    assert row["N_DIAS_FIM_SEMANA"] == 1
    assert row["VALOR_FIM_SEMANA_CENTAVOS"] == 1000
    assert row["SHARE_FIM_SEMANA"] == 0.5


def test_t02_requires_exact_operational_code():
    signals = detect_installment_transactions(_staged_fixture())

    assert len(signals) == 1
    assert signals.loc[0, "ID_TRANSACAO"] == "202501:00000004"
    assert signals.loc[0, "TRANSACAO"] == COMPRA_PARCELADA
    assert signals.loc[0, "NIVEL_TRIAGEM"] == "ATENCAO"
