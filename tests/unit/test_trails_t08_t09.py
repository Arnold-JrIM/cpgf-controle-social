from __future__ import annotations

import pandas as pd
import pytest

from cpgf.trails.t08_benford import (
    benford_probabilities,
    build_benford_signals,
    rank_relative_benford,
    sample_status,
)
from cpgf.trails.t09_limits import (
    T09_LEGAL_APPLICABILITY,
    build_limit_scenarios,
    build_normative_dimension,
    classify_scenario,
    classify_transactions_against_limits,
    detect_limit_context_signals,
)


def test_t08_probabilities_and_sample_status_boundaries():
    assert benford_probabilities("D1")["PROB_ESPERADA"].sum() == pytest.approx(1.0)
    assert benford_probabilities("D12")["PROB_ESPERADA"].sum() == pytest.approx(1.0)
    assert sample_status(299) == "NAO_APLICAR"
    assert sample_status(300) == "EXPLORATORIO"
    assert sample_status(999) == "EXPLORATORIO"
    assert sample_status(1000) == "FORMAL"
    assert sample_status(3000) == "FORMAL_ROBUSTEZ_MAIOR"


def test_t08_relative_p90_preserves_ties_and_builds_context_signals():
    indicators = pd.DataFrame(
        {
            "UG_ID": [f"UG{i:02d}" for i in range(10)],
            "ANO_TRANSACAO": [2025] * 10,
            "N_D12": [1000] * 10,
            "MAD_D12": [
                0.001,
                0.002,
                0.003,
                0.004,
                0.005,
                0.006,
                0.007,
                0.008,
                0.010,
                0.010,
            ],
        }
    )

    ranked = rank_relative_benford(indicators)
    signals = build_benford_signals(ranked)

    assert ranked["ANO_RANK_VALIDO"].all()
    assert ranked["LIMIAR_P90_MAD_D12"].iloc[0] == pytest.approx(0.010)
    assert int(ranked["TOP_DECIL_MAD_D12"].sum()) == 2
    assert len(signals) == 2
    assert set(signals["NIVEL_TRIAGEM"]) == {"ATENCAO"}
    assert signals["ID_SINAL"].str.startswith("T08_").all()


def test_t09_normative_dimension_and_exact_integer_cent_limits():
    dimension = build_normative_dimension()
    assert len(dimension) == 12

    purchases_2025 = dimension.loc[
        dimension["VIGENCIA_INICIO"].eq(pd.Timestamp("2025-01-01"))
        & dimension["CATEGORIA_CENARIO"].eq("COMPRAS_SERVICOS")
    ].iloc[0]
    engineering_2025 = dimension.loc[
        dimension["VIGENCIA_INICIO"].eq(pd.Timestamp("2025-01-01"))
        & dimension["CATEGORIA_CENARIO"].eq("OBRAS_ENGENHARIA")
    ].iloc[0]

    assert purchases_2025["LIMITE_PEQUENO_VULTO_CENTAVOS"] == 313_628
    assert engineering_2025["LIMITE_PEQUENO_VULTO_CENTAVOS"] == 627_256
    assert classify_scenario(313_627, 313_628) == "PROXIMO_LIMITE"
    assert classify_scenario(313_628, 313_628) == "NO_LIMITE"
    assert classify_scenario(313_629, 313_628) == "ACIMA_LIMITE"
    assert classify_scenario(200_000, 313_628) == "ABAIXO_FAIXA"


def _t09_fixture() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "ID_TRANSACAO": "tx-exact",
                "UG_ID": "000001",
                "FAVORECIDO_ID": "FORN-A",
                "DATA_DT": pd.Timestamp("2025-05-01"),
                "ANO_TRANSACAO": 2025,
                "VALOR_CENTAVOS": 313_628,
                "EH_COMPRA_NACIONAL": True,
            },
            {
                "ID_TRANSACAO": "tx-near",
                "UG_ID": "000001",
                "FAVORECIDO_ID": "FORN-A",
                "DATA_DT": pd.Timestamp("2025-05-02"),
                "ANO_TRANSACAO": 2025,
                "VALOR_CENTAVOS": 300_000,
                "EH_COMPRA_NACIONAL": True,
            },
            {
                "ID_TRANSACAO": "tx-above",
                "UG_ID": "000001",
                "FAVORECIDO_ID": "FORN-B",
                "DATA_DT": pd.Timestamp("2025-05-03"),
                "ANO_TRANSACAO": 2025,
                "VALOR_CENTAVOS": 700_000,
                "EH_COMPRA_NACIONAL": True,
            },
            {
                "ID_TRANSACAO": "tx-below",
                "UG_ID": "000001",
                "FAVORECIDO_ID": "FORN-C",
                "DATA_DT": pd.Timestamp("2025-05-04"),
                "ANO_TRANSACAO": 2025,
                "VALOR_CENTAVOS": 100_000,
                "EH_COMPRA_NACIONAL": True,
            },
        ]
    )


def test_t09_two_scenarios_combined_status_and_non_conclusive_applicability():
    staged = _t09_fixture()
    classified = classify_transactions_against_limits(staged)
    scenarios = build_limit_scenarios(classified)
    signals = detect_limit_context_signals(staged)

    assert len(classified) == 4
    assert len(scenarios) == 8
    assert scenarios.groupby("ID_TRANSACAO")["CATEGORIA_CENARIO"].nunique().eq(2).all()
    assert classified["APLICABILIDADE_JURIDICA"].eq(T09_LEGAL_APPLICABILITY).all()

    by_id = classified.set_index("ID_TRANSACAO")
    assert by_id.loc["tx-exact", "STATUS_COMPRAS"] == "NO_LIMITE"
    assert by_id.loc["tx-exact", "STATUS_T09"] == "NO_LIMITE_PELO_MENOS_UM_CENARIO"
    assert by_id.loc["tx-exact", "NIVEL_TRIAGEM"] == "INFORMATIVO"
    assert by_id.loc["tx-near", "STATUS_T09"] == "PROXIMO_LIMITE"
    assert by_id.loc["tx-above", "STATUS_T09"] == "ACIMA_AMBOS_CENARIOS"
    assert by_id.loc["tx-above", "NIVEL_TRIAGEM"] == "REFORCADO"
    assert by_id.loc["tx-below", "STATUS_T09"] == "ABAIXO_FAIXAS"
    assert len(signals) == 3
    assert signals["ID_SINAL"].str.startswith("T09_").all()
