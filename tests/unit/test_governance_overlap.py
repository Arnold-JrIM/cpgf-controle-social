import math

import pandas as pd

from cpgf.governance import (
    build_flag_records,
    build_supplier_year_flag_matrix,
    build_ug_year_flag_matrix,
    evaluate_flag_eligibility,
    marginal_by_annual_decile,
    marginal_by_supplier_exposure,
    marginal_contribution,
    pairwise_binary_metrics,
    pairwise_by_annual_decile,
    pairwise_by_supplier_exposure,
    square_metric_matrix,
)


def test_build_flag_records_projects_each_trail_to_frozen_diagnostic_keys():
    outputs = {
        "T01": pd.DataFrame(
            {"UG_ID": ["1"], "FAVORECIDO_ID": ["A"], "DATA_DT": [pd.Timestamp("2024-02-03")]}
        ),
        "T05": pd.DataFrame(
            {"UG_ID": ["1"], "FAVORECIDO_ID": ["B"], "ANO_TRANSACAO": [2024]}
        ),
        "T06": pd.DataFrame(
            {"UG_ID": ["1"], "TOP1_FAVORECIDO_ID": ["C"], "ANO_TRANSACAO": [2024]}
        ),
        "T07": pd.DataFrame({"UG_ID": ["1"], "ANO_TRANSACAO": [2024]}),
        "T08": pd.DataFrame({"UG_ID": ["1"], "ANO_TRANSACAO": [2024]}),
        "T09": pd.DataFrame(
            {"UG_ID": ["1"], "FAVORECIDO_ID": ["D"], "ANO_TRANSACAO": [2024]}
        ),
    }

    flags = build_flag_records(outputs).set_index("CODIGO_TRILHA")

    assert flags.loc["T01", "ANO"] == 2024
    assert flags.loc["T01", "CHAVE_ENTIDADE"] == "A"
    assert flags.loc["T06", "CHAVE_ENTIDADE"] == "C"
    assert pd.isna(flags.loc["T07", "CHAVE_ENTIDADE"])
    assert pd.isna(flags.loc["T08", "CHAVE_ENTIDADE"])
    assert flags.loc["T09", "CHAVE_ENTIDADE"] == "D"


def _flags_long_fixture() -> pd.DataFrame:
    return pd.DataFrame(
        [
            ("T01", "1", "A", 2024),
            ("T02", "1", "A", 2024),
            ("T03", "1", "B", 2024),
            ("T06", "1", "A", 2024),
            ("T07", "1", pd.NA, 2024),
            ("T08", "1", pd.NA, 2024),
            ("T09", "1", "B", 2024),
        ],
        columns=["CODIGO_TRILHA", "CODIGO_UG", "CHAVE_ENTIDADE", "ANO"],
    )


def test_supplier_matrix_separates_core_families_from_contexts():
    universe = pd.DataFrame(
        {
            "CODIGO_UG": ["1", "1", "2"],
            "CHAVE_ENTIDADE": ["A", "B", "C"],
            "ANO": [2024, 2024, 2024],
            "BANDA_EXPOSICAO_FORNECEDOR": ["B03_3_4", "B02_2", "B01_1"],
        }
    )

    matrix = build_supplier_year_flag_matrix(universe, _flags_long_fixture()).set_index(
        ["CODIGO_UG", "CHAVE_ENTIDADE"]
    )

    a = matrix.loc[("1", "A")]
    assert (a["T01"], a["T02"], a["T06"]) == (1, 1, 1)
    assert (a["F1"], a["F2"], a["F3"]) == (1, 0, 1)
    assert a["N_TRILHAS_ATIVAS"] == 3
    assert a["N_FAMILIAS_ATIVAS"] == 2
    assert a["T08_CONTEXTO"] == 1
    assert a["T09_CONTEXTO"] == 0

    b = matrix.loc[("1", "B")]
    assert b["T03"] == 1
    assert b["F2"] == 1
    assert b["T08_CONTEXTO"] == 1
    assert b["T09_CONTEXTO"] == 1
    assert b["N_TRILHAS_ATIVAS"] == 1


def test_ug_matrix_projects_supplier_flags_and_keeps_t08_t09_outside_core_count():
    universe = pd.DataFrame(
        {
            "CODIGO_UG": ["1", "2"],
            "ANO": [2024, 2024],
            "DECIL_EXPOSICAO_ANUAL": [10, 1],
        }
    )

    matrix = build_ug_year_flag_matrix(universe, _flags_long_fixture()).set_index("CODIGO_UG")
    row = matrix.loc["1"]

    assert [row[code] for code in ("T01", "T02", "T03", "T06", "T07")] == [1, 1, 1, 1, 1]
    assert row["N_TRILHAS_NUCLEO"] == 5
    assert row["N_FAMILIAS_NUCLEO"] == 4
    assert row["T08_CONTEXTO"] == 1
    assert row["T09_CONTEXTO"] == 1


def test_flag_eligibility_preserves_rare_and_constant_flags_as_diagnostics():
    frame = pd.DataFrame(
        {
            "A": [1] * 30 + [0] * 30,
            "B": [1] * 2 + [0] * 58,
            "C": [0] * 60,
        }
    )
    result = evaluate_flag_eligibility(frame, ["A", "B", "C"], "UG_ANO").set_index("REGRA")

    assert result.loc["A", "ELEGIBILIDADE_DIAGNOSTICO_ESTATISTICO"] == "SUFICIENTE"
    assert (
        result.loc["B", "ELEGIBILIDADE_DIAGNOSTICO_ESTATISTICO"]
        == "DIAGNOSTICO_ESTATISTICO_INSUFICIENTE"
    )
    assert result.loc["C", "ELEGIBILIDADE_DIAGNOSTICO_ESTATISTICO"] == "SEM_VARIACAO"
    assert bool(result.loc["A", "ELEGIVEL_PCA_VIF"])
    assert not bool(result.loc["B", "ELEGIVEL_PCA_VIF"])


def test_pairwise_metrics_match_frozen_jaccard_phi_and_conditionals():
    frame = pd.DataFrame({"A": [1, 1, 0, 0], "B": [1, 0, 1, 0]})
    result = pairwise_binary_metrics(
        frame,
        ["A", "B"],
        "UG_ANO",
        min_positives=1,
        min_negatives=1,
    ).iloc[0]

    assert result["INTERSECAO"] == 1
    assert result["A_APENAS"] == 1
    assert result["B_APENAS"] == 1
    assert result["NENHUMA"] == 1
    assert math.isclose(result["JACCARD"], 1 / 3)
    assert math.isclose(result["PHI"], 0.0)
    assert math.isclose(result["P_B_DADO_A"], 0.5)
    assert math.isclose(result["P_A_DADO_B"], 0.5)
    assert result["DIAGNOSTICO_PAR_NO_RECORTE"] == "SUFICIENTE"

    square = square_metric_matrix(pd.DataFrame([result]), ["A", "B"], "JACCARD")
    assert math.isclose(square.loc[0, "B"], 1 / 3)
    assert math.isclose(square.loc[1, "A"], 1 / 3)


def test_marginal_contribution_answers_loss_if_rule_is_removed():
    frame = pd.DataFrame(
        {
            "A": [1, 1, 0, 0],
            "B": [1, 0, 1, 0],
            "C": [0, 0, 1, 0],
        }
    )
    result = marginal_contribution(frame, ["A", "B", "C"], "UG_ANO").set_index(
        "REGRA_OU_FAMILIA"
    )

    assert result.loc["A", "N_UNIAO_MOTOR"] == 3
    assert result.loc["A", "N_EXCLUSIVOS"] == 1
    assert math.isclose(result.loc["A", "CONTRIBUICAO_MARGINAL_PCT"], 0.5)
    assert result.loc["A", "PERDA_UNIDADES_SE_REMOVER"] == 1
    assert result.loc["B", "N_EXCLUSIVOS"] == 0
    assert bool(result.loc["B", "ZERO_EXCLUSIVOS"])


def test_exposure_stratified_helpers_keep_strata_explicit():
    frame = pd.DataFrame(
        {
            "A": [1, 0, 1, 0],
            "B": [1, 1, 0, 0],
            "BANDA_EXPOSICAO_FORNECEDOR": ["B01_1", "B01_1", "B02_2", "B02_2"],
            "DECIL_EXPOSICAO_ANUAL": [1, 1, 10, 10],
        }
    )

    by_band = pairwise_by_supplier_exposure(frame, ["A", "B"])
    assert set(by_band["BANDA_EXPOSICAO_FORNECEDOR"]) == {"B01_1", "B02_2"}

    by_decile = pairwise_by_annual_decile(frame, ["A", "B"])
    assert set(by_decile["DECIL_EXPOSICAO_ANUAL"]) == {1, 10}

    marginal_band = marginal_by_supplier_exposure(frame, ["A", "B"])
    assert set(marginal_band["BANDA_EXPOSICAO_FORNECEDOR"]) == {"B01_1", "B02_2"}

    marginal_decile = marginal_by_annual_decile(frame, ["A", "B"])
    assert set(marginal_decile["DECIL_EXPOSICAO_ANUAL"]) == {1, 10}
