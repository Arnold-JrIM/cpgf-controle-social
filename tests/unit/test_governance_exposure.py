import pandas as pd
import pytest

from cpgf.governance import (
    BASELINE_COMPLETE_SUPPLIER_YEAR_N,
    BASELINE_COMPLETE_UG_YEAR_N,
    add_supplier_exposure_bands,
    add_ug_annual_exposure_deciles,
    build_supplier_year_universe,
    build_ug_year_universe,
)


def _staged_fixture() -> pd.DataFrame:
    rows = [
        # U1 / 2024: compras elegíveis para fornecedor e UG.
        ("U1", "F1", True, "P1", "2024-01-01", 2024, 100, True, False, False),
        ("U1", "F1", True, "P2", "2024-01-02", 2024, 200, True, False, False),
        ("U1", "F2", True, "P1", "2024-01-03", 2024, 300, True, False, False),
        # Compra ajustada: excluída dos dois universos.
        ("U1", "F2", True, "P1", "2024-01-04", 2024, 350, True, False, True),
        # Compra sem fornecedor identificado: entra em UG × ano, não em fornecedor × ano.
        ("U1", None, False, "P3", "2024-01-05", 2024, 400, True, False, False),
        # Saque: entra apenas em UG × ano.
        ("U1", None, False, "P1", "2024-01-06", 2024, 500, False, True, False),
        # Valor zero: excluído.
        ("U1", "F3", True, "P1", "2024-01-07", 2024, 0, True, False, False),
        # Data ausente: excluída.
        ("U1", "F4", True, "P1", None, 2024, 600, True, False, False),
        # U2 / 2024: uma operação efetiva para testar ranking anual.
        ("U2", "F5", True, "P4", "2024-02-01", 2024, 700, True, False, False),
        # Períodos parciais preservados no universo completo.
        ("U1", "F1", True, "P1", "2012-12-01", 2012, 800, True, False, False),
        ("U3", "F6", True, "P5", "2026-01-01", 2026, 900, True, False, False),
    ]
    frame = pd.DataFrame(
        rows,
        columns=[
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
        ],
    )
    frame["DATA_DT"] = pd.to_datetime(frame["DATA_DT"])
    return frame


def test_supplier_exposure_bands_cover_frozen_ranges():
    frame = pd.DataFrame(
        {"N_COMPRAS_FORNECEDOR": [1, 2, 3, 4, 5, 9, 10, 19, 20, 40]}
    )

    result = add_supplier_exposure_bands(frame)

    assert result["BANDA_EXPOSICAO_FORNECEDOR"].tolist() == [
        "B01_1",
        "B02_2",
        "B03_3_4",
        "B03_3_4",
        "B04_5_9",
        "B04_5_9",
        "B05_10_19",
        "B05_10_19",
        "B06_20_MAIS",
        "B06_20_MAIS",
    ]
    assert result["ORDEM_BANDA_EXPOSICAO_FORNECEDOR"].tolist() == [
        1,
        2,
        3,
        3,
        4,
        4,
        5,
        5,
        6,
        6,
    ]


def test_ug_deciles_are_annual_and_preserve_ties_by_average_rank():
    frame = pd.DataFrame(
        {
            "ANO": [2024] * 10 + [2025] * 4,
            "N_OPERACOES_EFETIVAS": list(range(1, 11)) + [1, 1, 2, 2],
        }
    )

    result = add_ug_annual_exposure_deciles(frame)

    assert result.loc[:9, "DECIL_EXPOSICAO_ANUAL"].tolist() == list(range(1, 11))
    assert result.loc[10:, "DECIL_EXPOSICAO_ANUAL"].tolist() == [4, 4, 9, 9]
    assert result.loc[10, "PERCENTIL_EXPOSICAO_ANUAL"] == pytest.approx(0.375)
    assert result.loc[12, "PERCENTIL_EXPOSICAO_ANUAL"] == pytest.approx(0.875)


def test_supplier_year_universe_matches_frozen_eligibility_and_metrics():
    result = build_supplier_year_universe(_staged_fixture())

    assert len(result) == 5
    u1_f1_2024 = result.loc[
        (result["CODIGO_UG"] == "U1")
        & (result["CHAVE_ENTIDADE"] == "F1")
        & (result["ANO"] == 2024)
    ].iloc[0]
    assert u1_f1_2024["N_COMPRAS_FORNECEDOR"] == 2
    assert u1_f1_2024["VALOR_COMPRAS_FORNECEDOR"] == pytest.approx(3.0)
    assert u1_f1_2024["N_PORTADORES_FORNECEDOR"] == 2
    assert u1_f1_2024["N_DIAS_COMPRA_FORNECEDOR"] == 2
    assert u1_f1_2024["BANDA_EXPOSICAO_FORNECEDOR"] == "B02_2"
    assert u1_f1_2024["STATUS_PERIODO"] == "COMPLETO"

    assert not (result["CHAVE_ENTIDADE"].isna()).any()
    assert set(result["ANO"].tolist()) == {2012, 2024, 2026}

    complete = build_supplier_year_universe(_staged_fixture(), complete_years_only=True)
    assert len(complete) == 3
    assert complete["STATUS_PERIODO"].eq("COMPLETO").all()
    assert complete["ANO"].eq(2024).all()


def test_ug_year_universe_counts_effective_operations_and_supplier_observability():
    result = build_ug_year_universe(_staged_fixture())

    assert len(result) == 4
    u1_2024 = result.loc[
        (result["CODIGO_UG"] == "U1") & (result["ANO"] == 2024)
    ].iloc[0]
    assert u1_2024["N_COMPRAS_UG"] == 4
    assert u1_2024["VALOR_COMPRAS_UG"] == pytest.approx(10.0)
    assert u1_2024["N_SAQUES_UG"] == 1
    assert u1_2024["VALOR_SAQUES_UG"] == pytest.approx(5.0)
    assert u1_2024["N_OPERACOES_EFETIVAS"] == 5
    assert u1_2024["N_PORTADORES_UG"] == 3
    assert u1_2024["N_FORNECEDORES_UG"] == 2
    assert u1_2024["N_DIAS_ATIVOS_UG"] == 5
    assert u1_2024["DECIL_EXPOSICAO_ANUAL"] == 10
    assert u1_2024["STATUS_PERIODO"] == "COMPLETO"

    u2_2024 = result.loc[
        (result["CODIGO_UG"] == "U2") & (result["ANO"] == 2024)
    ].iloc[0]
    assert u2_2024["N_OPERACOES_EFETIVAS"] == 1
    assert u2_2024["DECIL_EXPOSICAO_ANUAL"] == 5

    complete = build_ug_year_universe(_staged_fixture(), complete_years_only=True)
    assert len(complete) == 2
    assert complete["ANO"].eq(2024).all()


def test_frozen_complete_year_universe_counts_are_exposed_as_regression_contract():
    assert BASELINE_COMPLETE_SUPPLIER_YEAR_N == 522_053
    assert BASELINE_COMPLETE_UG_YEAR_N == 13_785


def test_universe_builder_fails_loudly_when_staging_contract_is_incomplete():
    with pytest.raises(ValueError, match="Colunas ausentes"):
        build_ug_year_universe(pd.DataFrame({"UG_ID": ["U1"]}))
