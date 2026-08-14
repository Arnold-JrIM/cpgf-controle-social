from __future__ import annotations

import pandas as pd

from cpgf.trails.t06_vendor_concentration import detect_vendor_concentration_signals
from cpgf.trails.t07_withdrawals import (
    detect_daily_multiwithdrawal_episodes,
    detect_withdrawal_recurrence_signals,
)


def test_t06_detects_eligible_top1_concentration():
    rows = []
    suppliers = [("A", 12), ("B", 4), ("C", 4)]
    transaction = 0
    for supplier, count in suppliers:
        for _ in range(count):
            transaction += 1
            rows.append(
                {
                    "ID_TRANSACAO": f"tx-{transaction}",
                    "UG_ID": "000001",
                    "ANO_TRANSACAO": 2025,
                    "FAVORECIDO_ID": supplier,
                    "FAVORECIDO_IDENTIFICADO": True,
                    "VALOR_CENTAVOS": 10_000,
                    "EH_COMPRA_NACIONAL": True,
                    "DATA_DT": pd.Timestamp("2025-01-02"),
                }
            )

    signals = detect_vendor_concentration_signals(pd.DataFrame(rows))

    assert len(signals) == 1
    signal = signals.iloc[0]
    assert signal["N_COMPRAS_IDENTIFICADAS"] == 20
    assert signal["N_FORNECEDORES"] == 3
    assert signal["TOP1_FAVORECIDO_ID"] == "A"
    assert signal["TOP1_SHARE_VALOR"] == 0.60
    assert signal["COBERTURA_VALOR_IDENTIFICADO"] == 1.0
    assert signal["NIVEL_TRIAGEM"] == "ATENCAO"
    assert signal["ID_SINAL"].startswith("T06_")


def _withdrawal_rows(days_by_cardholder: dict[str, int]) -> pd.DataFrame:
    rows = []
    sequence = 0
    for cardholder, n_days in days_by_cardholder.items():
        for day in range(1, n_days + 1):
            for withdrawal in range(2):
                sequence += 1
                rows.append(
                    {
                        "ID_TRANSACAO": f"w-{sequence}",
                        "UG_ID": "000001",
                        "PORTADOR_ID": f"000001|{cardholder}|NOME {cardholder}",
                        "PORTADOR_ID_BASELINE": cardholder,
                        "DATA_DT": pd.Timestamp(2025, 1, day),
                        "ANO_TRANSACAO": 2025,
                        "VALOR_CENTAVOS": 10_000 + withdrawal,
                        "TRANSAÇÃO": "SAQUE CASH/ATM BB",
                        "EH_SAQUE_EFETIVO": True,
                    }
                )
    return pd.DataFrame(rows)


def test_t07_prioritizes_only_high_annual_recurrence_with_ten_comparables():
    staged = _withdrawal_rows({"P0": 4, **{f"P{i}": 1 for i in range(1, 10)}})

    daily = detect_daily_multiwithdrawal_episodes(staged)
    signals = detect_withdrawal_recurrence_signals(staged)

    assert len(daily) == 13
    assert len(signals) == 1
    signal = signals.iloc[0]
    assert signal["PORTADOR_ID"].endswith("P0|NOME P0")
    assert signal["N_DIAS_MULTISAQUE"] == 4
    assert signal["N_PORTADORES_COMPARAVEIS_ANO"] == 10
    assert signal["PRIORITARIO"]
    assert signal["ID_SINAL"].startswith("T07_")


def test_t07_can_replay_historical_cardholder_identity_explicitly():
    staged = _withdrawal_rows({"111": 2, "222": 2, **{f"P{i}": 1 for i in range(1, 10)}})

    # Simula a colisão histórica: dois portadores compostos distintos compartilham
    # a mesma identidade mascarada na Preparação 1.0.0, mas em datas distintas.
    mask_second = staged["PORTADOR_ID"].str.contains("222", regex=False)
    staged.loc[mask_second, "PORTADOR_ID_BASELINE"] = "111"
    staged.loc[mask_second, "PORTADOR_ID"] = "000001|111|NOME B"
    mask_first = staged["PORTADOR_ID"].str.contains("111", regex=False) & ~mask_second
    staged.loc[mask_first, "PORTADOR_ID"] = "000001|111|NOME A"
    staged.loc[mask_second, "DATA_DT"] = staged.loc[mask_second, "DATA_DT"] + pd.Timedelta(days=2)

    production = detect_withdrawal_recurrence_signals(staged)
    baseline = detect_withdrawal_recurrence_signals(
        staged, portador_column="PORTADOR_ID_BASELINE"
    )

    assert production.empty
    assert len(baseline) == 1
    assert baseline.iloc[0]["PORTADOR_ID"] == "111"
    assert baseline.iloc[0]["N_DIAS_MULTISAQUE"] == 4
