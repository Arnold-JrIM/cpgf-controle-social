import math

import numpy as np
import pandas as pd

from cpgf.governance import (
    condition_indices,
    multicollinearity_by_group,
    pca_by_group,
    principal_component_diagnostics,
    variance_inflation_factors,
)


def _balanced_independent_binary_frame(repeats: int = 10) -> pd.DataFrame:
    rows = []
    for _ in range(repeats):
        for a in (0, 1):
            for b in (0, 1):
                for c in (0, 1):
                    rows.append((a, b, c))
    return pd.DataFrame(rows, columns=["A", "B", "C"])


def test_vif_is_one_for_balanced_orthogonal_binary_flags():
    frame = _balanced_independent_binary_frame()
    result = variance_inflation_factors(frame, ["A", "B", "C"], "UG_ANO").set_index(
        "REGRA_OU_FAMILIA"
    )

    for flag in ("A", "B", "C"):
        assert math.isclose(result.loc[flag, "R2_AUXILIAR"], 0.0, abs_tol=1e-12)
        assert math.isclose(result.loc[flag, "VIF"], 1.0, abs_tol=1e-12)
        assert result.loc[flag, "STATUS_VIF"] == "CALCULADO"


def test_vif_marks_perfect_linear_dependency_as_infinite():
    frame = pd.DataFrame({"A": [0] * 40 + [1] * 40})
    frame["B"] = frame["A"]
    frame["C"] = [0, 1] * 40

    result = variance_inflation_factors(frame, ["A", "B", "C"], "UG_ANO").set_index(
        "REGRA_OU_FAMILIA"
    )

    assert np.isinf(result.loc["A", "VIF"])
    assert np.isinf(result.loc["B", "VIF"])
    assert result.loc["A", "STATUS_VIF"] == "DEPENDENCIA_LINEAR_PERFEITA"
    assert result.loc["B", "STATUS_VIF"] == "DEPENDENCIA_LINEAR_PERFEITA"


def test_rare_flag_remains_in_vif_output_but_is_not_calculated():
    frame = pd.DataFrame(
        {
            "A": [0] * 40 + [1] * 40,
            "RARE": [1, 1] + [0] * 78,
        }
    )

    result = variance_inflation_factors(frame, ["A", "RARE"], "UG_ANO").set_index(
        "REGRA_OU_FAMILIA"
    )

    assert result.loc["RARE", "ELEGIBILIDADE_DIAGNOSTICO_ESTATISTICO"] == (
        "DIAGNOSTICO_ESTATISTICO_INSUFICIENTE"
    )
    assert pd.isna(result.loc["RARE", "VIF"])
    assert result.loc["RARE", "STATUS_VIF"].startswith("NAO_CALCULADO_")


def test_condition_indices_detect_exact_singularity():
    frame = pd.DataFrame({"A": [0] * 40 + [1] * 40})
    frame["B"] = frame["A"]

    result = condition_indices(frame, ["A", "B"], "UG_ANO")

    assert len(result) == 2
    assert bool(result.iloc[-1]["SINGULAR"])
    assert np.isinf(result.iloc[-1]["INDICE_CONDICAO"])
    assert math.isclose(result.iloc[0]["AUTOVALOR"], 2.0, rel_tol=1e-12)


def test_pca_balanced_orthogonal_flags_has_equal_explained_variance():
    frame = _balanced_independent_binary_frame()
    diagnostics = principal_component_diagnostics(frame, ["A", "B", "C"], "UG_ANO")
    components = diagnostics["components"]

    assert len(components) == 3
    assert np.allclose(components["AUTOVALOR"].to_numpy(), [1.0, 1.0, 1.0])
    assert np.allclose(
        components["VARIANCIA_EXPLICADA"].to_numpy(),
        [1 / 3, 1 / 3, 1 / 3],
    )
    assert math.isclose(components.iloc[-1]["VARIANCIA_EXPLICADA_ACUMULADA"], 1.0)


def test_pca_duplicate_flags_concentrates_variance_in_first_component():
    frame = pd.DataFrame({"A": [0] * 40 + [1] * 40})
    frame["B"] = frame["A"]

    diagnostics = principal_component_diagnostics(frame, ["A", "B"], "UG_ANO")
    components = diagnostics["components"]

    assert np.allclose(components["AUTOVALOR"].to_numpy(), [2.0, 0.0])
    assert np.allclose(components["VARIANCIA_EXPLICADA"].to_numpy(), [1.0, 0.0])
    loadings = diagnostics["loadings"]
    pc1 = loadings.loc[loadings["COMPONENTE"].eq("PC1")].set_index("REGRA_OU_FAMILIA")
    assert pc1.loc["A", "CARGA_CORRELACAO"] > 0
    assert pc1.loc["B", "CARGA_CORRELACAO"] > 0


def test_group_helpers_keep_exposure_stratum_explicit():
    frame = pd.concat(
        [
            _balanced_independent_binary_frame(repeats=10).assign(BANDA="B01"),
            _balanced_independent_binary_frame(repeats=10).assign(BANDA="B02"),
        ],
        ignore_index=True,
    )

    multi = multicollinearity_by_group(
        frame, ["A", "B", "C"], "UG_FORNECEDOR_ANO", "BANDA"
    )
    assert set(multi["vif"]["RECORTE_VALOR"]) == {"B01", "B02"}

    pca = pca_by_group(frame, ["A", "B", "C"], "UG_FORNECEDOR_ANO", "BANDA")
    assert set(pca["components"]["RECORTE_VALOR"]) == {"B01", "B02"}
