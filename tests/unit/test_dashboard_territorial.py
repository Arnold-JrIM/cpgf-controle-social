from types import SimpleNamespace

import pandas as pd
import pytest

from cpgf.dashboard.data import DashboardDataContext
from cpgf.dashboard.territorial import (
    geographic_available_years,
    geographic_metric_catalog,
    geographic_uf_metric,
    territorial_ug_context,
)
from cpgf.geography.maps import attach_uf_plot_anchors, uf_plot_anchors
from cpgf.serving import ServingRepository, persist_serving_tables


def _context(tmp_path):
    geo_catalog = pd.DataFrame(
        {
            "REFERENCIA_TEMPORAL": ["TRANSACAO", "EXTRATO"],
            "METRICA": ["VALOR_TRANSACIONADO_OBSERVAVEL", "VALOR_TOTAL_REGISTRADO"],
            "ROTULO": ["Valor transacionado observável", "Valor total registrado"],
            "UNIDADE": ["BRL", "BRL"],
            "METRICA_PRINCIPAL": [True, True],
        }
    )
    geo_long = pd.DataFrame(
        {
            "ANO": [2024, 2024, 2025, 2025],
            "UF": ["DF", "SP", "DF", "SP"],
            "STATUS_PERIODO": [
                "EXERCICIO_COMPLETO",
                "EXERCICIO_COMPLETO",
                "EXERCICIO_COMPLETO",
                "EXERCICIO_COMPLETO",
            ],
            "REFERENCIA_TEMPORAL": ["TRANSACAO"] * 4,
            "METRICA": ["VALOR_TRANSACIONADO_OBSERVAVEL"] * 4,
            "ROTULO_METRICA": ["Valor transacionado observável"] * 4,
            "UNIDADE": ["BRL"] * 4,
            "VALOR_METRICA": [100.0, 200.0, 150.0, 250.0],
        }
    )
    dimension = pd.DataFrame(
        {
            "UG_ID": ["001", "002"],
            "UF_UG": ["DF", "SP"],
            "TITULO_UG_SIAFI": ["UG Distrito Federal", "UG São Paulo"],
        }
    )
    ug = pd.DataFrame(
        {
            "CODIGO_UG": ["001", "002"],
            "ANO": [2025, 2025],
            "N_OPERACOES_EFETIVAS": [3, 5],
            "VALOR_COMPRAS_UG": [100.0, 200.0],
            "VALOR_SAQUES_UG": [10.0, 20.0],
            "N_TRILHAS_NUCLEO": [1, 0],
            "N_FAMILIAS_NUCLEO": [1, 0],
            "STATUS_PERIODO": ["COMPLETO", "COMPLETO"],
        }
    )
    persist_serving_tables(
        {
            "geo_metric_catalog": geo_catalog,
            "geo_uf_ano_dashboard_long": geo_long,
            "dim_ug_geografica": dimension,
            "matrix_ug_year": ug,
        },
        tmp_path,
    )
    repository = ServingRepository(tmp_path / "cpgf_serving.duckdb")
    return DashboardDataContext(repository=repository, bootstrap=SimpleNamespace(status="LOCAL"))


def test_geographic_catalog_and_years_are_read_from_serving(tmp_path):
    context = _context(tmp_path)
    catalog = geographic_metric_catalog(context, reference="TRANSACAO")
    assert catalog["METRICA"].tolist() == ["VALOR_TRANSACIONADO_OBSERVAVEL"]
    assert geographic_available_years(context, "TRANSACAO") == [2024, 2025]


def test_geographic_metric_query_uses_materialized_uf_year_values(tmp_path):
    context = _context(tmp_path)
    frame = geographic_uf_metric(
        context,
        reference="TRANSACAO",
        year=2025,
        metric="VALOR_TRANSACIONADO_OBSERVAVEL",
    )
    assert frame["UF"].tolist() == ["SP", "DF"]
    assert frame["VALOR_METRICA"].tolist() == [250.0, 150.0]


def test_geographic_metric_rejects_metric_from_other_reference(tmp_path):
    context = _context(tmp_path)
    with pytest.raises(ValueError):
        geographic_uf_metric(
            context,
            reference="TRANSACAO",
            year=2025,
            metric="VALOR_TOTAL_REGISTRADO",
        )


def test_territorial_ug_context_joins_only_materialized_views(tmp_path):
    context = _context(tmp_path)
    frame = territorial_ug_context(context, uf="DF", year=2025)
    assert frame["CODIGO_UG"].tolist() == ["001"]
    assert frame["TITULO_UG_SIAFI"].tolist() == ["UG Distrito Federal"]
    assert frame["VALOR_TOTAL"].tolist() == [110.0]
    assert frame["N_TRILHAS_NUCLEO"].tolist() == [1]


def test_map_anchors_cover_all_brazilian_ufs_and_attach_without_changing_values():
    anchors = uf_plot_anchors()
    assert len(anchors) == 27
    assert anchors["UF"].nunique() == 27

    frame = pd.DataFrame({"UF": ["DF", "SP"], "VALOR_METRICA": [10.0, 20.0]})
    mapped = attach_uf_plot_anchors(frame)
    assert mapped["VALOR_METRICA"].tolist() == [10.0, 20.0]
    assert mapped["LATITUDE"].notna().all()
    assert mapped["LONGITUDE"].notna().all()
