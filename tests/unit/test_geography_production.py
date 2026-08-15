from __future__ import annotations

from pathlib import Path

import pandas as pd

from cpgf.geography.aggregates import build_geographic_aggregates, metric_catalog
from cpgf.geography.enrichment import extract_year_with_fallback
from cpgf.geography.ug_dimension import MANUAL_COMPLEMENTS, build_ug_geographic_dimension


def _write_synthetic_siafi(path: Path) -> None:
    with path.open("w", encoding="utf-8") as handle:
        handle.write('"UG","Título","UF","Código Órgão","Resto"\n')
        for value in range(49_547):
            handle.write(f'"{value}","UG {value}","DF","1","x"\n')


def test_build_ug_dimension_ports_frozen_shape_and_manual_provenance(tmp_path):
    source = tmp_path / "siafi.csv"
    _write_synthetic_siafi(source)
    dimension = build_ug_geographic_dimension(source, require_frozen_source=False)

    assert len(dimension) == 49_552
    assert dimension["UG_ID"].nunique() == 49_552
    manual = dimension.loc[dimension["TIPO_FONTE_UF"].eq("COMPLEMENTO_MANUAL")]
    assert set(manual["UG_ID"]) == set(MANUAL_COMPLEMENTS)
    assert set(manual["VERSAO_FONTE_UF"]) == {"2026-08-13"}


def test_extract_year_fallback_is_local_to_geography():
    staged = pd.DataFrame(
        {
            "ANO_EXTRATO_REF": pd.Series([2025, pd.NA], dtype="Int64"),
            "COMPETENCIA_ARQUIVO": ["202501", "202402"],
        }
    )
    assert extract_year_with_fallback(staged).tolist() == [2025, 2024]


def test_geographic_aggregates_keep_transaction_and_extract_references_separate():
    staged = pd.DataFrame(
        {
            "UG_ID": ["000001", "000001", "000002"],
            "ANO_TRANSACAO": pd.Series([2025, pd.NA, 2025], dtype="Int64"),
            "ANO_EXTRATO_REF": pd.Series([2025, 2025, 2025], dtype="Int64"),
            "DATA_DT": pd.to_datetime(["2025-01-01", None, "2025-01-03"]),
            "VALOR_CENTAVOS": pd.Series([10_000, 20_000, 30_000], dtype="Int64"),
            "EH_COMPRA_EFETIVA": [True, False, False],
            "EH_SAQUE_EFETIVO": [False, False, True],
            "EH_AJUSTE_CONTESTACAO": [False, False, False],
            "EH_SIGILOSO": [False, True, False],
        }
    )
    dimension = pd.DataFrame(
        {"UG_ID": ["000001", "000002"], "UF_UG": ["DF", "SP"]}
    )
    tables = build_geographic_aggregates(staged, dimension)
    transaction = tables["geo_uf_ano_transacao"]
    extract = tables["geo_uf_ano_extrato"]

    assert transaction["N_TRANSACOES_OBSERVAVEIS"].sum() == 2
    assert transaction["VALOR_TRANSACIONADO_OBSERVAVEL"].sum() == 400.0
    assert extract["N_REGISTROS"].sum() == 3
    assert extract["VALOR_TOTAL_REGISTRADO"].sum() == 600.0
    assert extract["VALOR_SIGILOSO"].sum() == 200.0
    assert extract["VALOR_COM_DATA_TRANSACAO_OBSERVAVEL"].sum() == 400.0
    assert len(metric_catalog()) == 17


def test_geographic_aggregates_do_not_treat_adjustment_as_positive_operation():
    staged = pd.DataFrame(
        {
            "UG_ID": ["000001", "000001"],
            "ANO_TRANSACAO": pd.Series([2025, 2025], dtype="Int64"),
            "ANO_EXTRATO_REF": pd.Series([2025, 2025], dtype="Int64"),
            "DATA_DT": pd.to_datetime(["2025-01-01", "2025-01-02"]),
            "VALOR_CENTAVOS": pd.Series([10_000, 99_999], dtype="Int64"),
            "EH_COMPRA_EFETIVA": [True, False],
            "EH_SAQUE_EFETIVO": [False, False],
            "EH_AJUSTE_CONTESTACAO": [False, True],
            "EH_SIGILOSO": [False, False],
        }
    )
    dimension = pd.DataFrame({"UG_ID": ["000001"], "UF_UG": ["DF"]})
    tables = build_geographic_aggregates(staged, dimension)
    assert tables["geo_uf_ano_extrato"]["VALOR_TOTAL_REGISTRADO"].sum() == 100.0
