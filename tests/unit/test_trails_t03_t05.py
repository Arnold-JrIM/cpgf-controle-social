from __future__ import annotations

import pandas as pd

from cpgf.preprocessing.build_staging import build_staging_frame
from cpgf.preprocessing.transaction_types import COMPRA_NACIONAL
from cpgf.trails.t03_exact_repetition import (
    detect_exact_repetition_groups,
    detect_integral_observable_repetitions,
    link_exact_repetition_transactions,
)
from cpgf.trails.t04_multi_cardholder import (
    detect_multi_cardholder_groups,
    link_multi_cardholder_transactions,
)
from cpgf.trails.t05_vendor_recurrence import (
    compute_t05_candidate_windows,
    detect_vendor_recurrence_episodes,
    link_vendor_recurrence_transactions,
)


def _staged_rows(rows: list[dict[str, object]]) -> pd.DataFrame:
    frame = pd.DataFrame(rows)
    frame["DATA_DT"] = pd.to_datetime(frame["DATA_DT"])
    frame["ANO_TRANSACAO"] = frame["DATA_DT"].dt.year.astype("Int64")
    frame["VALOR_CENTAVOS"] = frame["VALOR_CENTAVOS"].astype("Int64")
    frame["VALOR_NUM"] = (frame["VALOR_CENTAVOS"].astype("Float64") / 100.0).astype("Float64")
    frame["TRANSAÇÃO"] = COMPRA_NACIONAL
    frame["EH_COMPRA_EFETIVA"] = True
    frame["EH_COMPRA_NACIONAL"] = True
    frame["EH_AJUSTE_CONTESTACAO"] = False
    frame["FAVORECIDO_IDENTIFICADO"] = True
    frame["COMPETENCIA_ARQUIVO"] = "202501"
    frame["ARQUIVO_ORIGEM"] = "202501_CPGF.csv"
    frame["ID_TRANSACAO"] = [f"TX-{index:03d}" for index in range(1, len(frame) + 1)]
    return frame


def test_t03_groups_repetition_and_keeps_transaction_bridge():
    staged = _staged_rows(
        [
            {
                "UG_ID": "000001",
                "PORTADOR_ID": "000001|111|PORTADOR A",
                "PORTADOR_ID_BASELINE": "111",
                "FAVORECIDO_ID": "12345678000199",
                "DATA_DT": "2025-01-02",
                "VALOR_CENTAVOS": 10000,
            }
            for _ in range(3)
        ]
    )

    groups = detect_exact_repetition_groups(staged)
    bridge = link_exact_repetition_transactions(staged, groups)

    assert len(groups) == 1
    assert groups.loc[0, "N_TRANSACOES"] == 3
    assert groups.loc[0, "NIVEL_TRIAGEM"] == "REFORCADO"
    assert groups.loc[0, "VALOR_TOTAL_CENTAVOS"] == 30000
    assert groups.loc[0, "ID_SINAL"].startswith("T03_")
    assert len(bridge) == 3
    assert bridge["ID_SINAL"].nunique() == 1


def test_t03_can_replay_historical_cardholder_identity_explicitly():
    staged = _staged_rows(
        [
            {
                "UG_ID": "000001",
                "PORTADOR_ID": "000001|111|PORTADOR A",
                "PORTADOR_ID_BASELINE": "111",
                "FAVORECIDO_ID": "12345678000199",
                "DATA_DT": "2025-01-02",
                "VALOR_CENTAVOS": 10000,
            },
            {
                "UG_ID": "000001",
                "PORTADOR_ID": "000001|111|PORTADOR B",
                "PORTADOR_ID_BASELINE": "111",
                "FAVORECIDO_ID": "12345678000199",
                "DATA_DT": "2025-01-02",
                "VALOR_CENTAVOS": 10000,
            },
        ]
    )

    production = detect_exact_repetition_groups(staged)
    baseline = detect_exact_repetition_groups(staged, portador_column="PORTADOR_ID_BASELINE")

    assert production.empty
    assert len(baseline) == 1
    assert baseline.loc[0, "N_TRANSACOES"] == 2


def test_t04_counts_distinct_cardholders_and_links_rows():
    rows = []
    for index in range(5):
        rows.append(
            {
                "UG_ID": "000002",
                "PORTADOR_ID": f"000002|22{index}|PORTADOR {index}",
                "PORTADOR_ID_BASELINE": f"22{index}",
                "FAVORECIDO_ID": "99887766000155",
                "DATA_DT": "2025-02-10",
                "VALOR_CENTAVOS": 25000,
            }
        )
    staged = _staged_rows(rows)

    groups = detect_multi_cardholder_groups(staged)
    bridge = link_multi_cardholder_transactions(staged, groups)

    assert len(groups) == 1
    assert groups.loc[0, "N_PORTADORES"] == 5
    assert groups.loc[0, "NIVEL_TRIAGEM"] == "MUITO_ELEVADO"
    assert groups.loc[0, "VALOR_TOTAL_CENTAVOS"] == 125000
    assert len(bridge) == 5


def test_t05_builds_overlapping_windows_then_keeps_strongest_episode():
    dates = ["2025-03-01", "2025-03-05", "2025-03-10", "2025-03-15", "2025-03-20", "2025-03-25"]
    amounts = [10000, 10100, 9900, 10050, 9950, 10020]
    rows = []
    for index, (date, amount) in enumerate(zip(dates, amounts, strict=True)):
        portador = "A" if index % 2 == 0 else "B"
        rows.append(
            {
                "UG_ID": "000003",
                "PORTADOR_ID": f"000003|{portador}|PORTADOR {portador}",
                "PORTADOR_ID_BASELINE": portador,
                "FAVORECIDO_ID": "11223344000188",
                "DATA_DT": date,
                "VALOR_CENTAVOS": amount,
            }
        )
    staged = _staged_rows(rows)

    candidates = compute_t05_candidate_windows(staged)
    episodes = detect_vendor_recurrence_episodes(staged)
    bridge = link_vendor_recurrence_transactions(staged, episodes)

    assert len(candidates) == 2
    assert len(episodes) == 1
    episode = episodes.iloc[0]
    assert episode["N_TRANSACOES"] == 6
    assert episode["N_PORTADORES"] == 2
    assert episode["NIVEL_TRIAGEM"] == "REFORCADO"
    assert episode["SHARE_DENTRO_FAIXA_MEDIANA"] == 1.0
    assert bool(episode["SIMILARIDADE_ROBUSTA_ALTA"])
    assert episode["ID_SINAL"].startswith("T05_")
    assert len(bridge) == 6


def test_t03b_hashes_only_the_fifteen_observable_business_fields():
    raw_row = {
        "CÓDIGO ÓRGÃO SUPERIOR": "10000",
        "NOME ÓRGÃO SUPERIOR": "ORGAO SUPERIOR",
        "CÓDIGO ÓRGÃO": "10001",
        "NOME ÓRGÃO": "ORGAO",
        "CÓDIGO UNIDADE GESTORA": "1",
        "NOME UNIDADE GESTORA": "UG TESTE",
        "ANO EXTRATO": "2025",
        "MÊS EXTRATO": "01",
        "CPF PORTADOR": "***.111.222-**",
        "NOME PORTADOR": "PORTADOR TESTE",
        "CNPJ OU CPF FAVORECIDO": "12345678000199",
        "NOME FAVORECIDO": "FORNECEDOR TESTE",
        "TRANSAÇÃO": COMPRA_NACIONAL,
        "DATA TRANSAÇÃO": "02/01/2025",
        "VALOR TRANSAÇÃO": "100,00",
    }
    raw = pd.DataFrame([raw_row, raw_row.copy()])
    staged = build_staging_frame(raw)
    staged["ID_TRANSACAO"] = ["RAW-1", "RAW-2"]

    diagnostic = detect_integral_observable_repetitions(staged)

    assert len(diagnostic["groups"]) == 1
    assert diagnostic["groups"].loc[0, "N_REPETICOES"] == 2
    assert len(diagnostic["transactions"]) == 2
    assert diagnostic["transactions"]["ID_GRUPO_INTEGRAL"].nunique() == 1
