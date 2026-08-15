from types import SimpleNamespace

import pandas as pd
import pytest

from cpgf.dashboard.data import (
    DashboardDataContext,
    DashboardFilter,
    annual_overview,
    overview_summary,
    top_ugs,
    trail_prevalence,
)
from cpgf.serving import ServingRepository, persist_serving_tables


def _context(tmp_path):
    ug = pd.DataFrame(
        {
            "CODIGO_UG": ["001", "001", "002"],
            "ANO": [2024, 2025, 2025],
            "N_COMPRAS_UG": [10, 8, 5],
            "VALOR_COMPRAS_UG": [1000.0, 800.0, 500.0],
            "N_SAQUES_UG": [1, 0, 1],
            "VALOR_SAQUES_UG": [100.0, 0.0, 50.0],
            "N_OPERACOES_EFETIVAS": [11, 8, 6],
            "N_PORTADORES_UG": [2, 2, 1],
            "N_FORNECEDORES_UG": [4, 3, 2],
            "N_DIAS_ATIVOS_UG": [7, 5, 4],
            "STATUS_PERIODO": ["COMPLETO", "COMPLETO", "COMPLETO"],
            "PERCENTIL_EXPOSICAO_ANUAL": [1.0, 1.0, 0.5],
            "DECIL_EXPOSICAO_ANUAL": [10, 10, 5],
            "T01": [1, 0, 0],
            "T02": [0, 0, 0],
            "T03": [0, 1, 0],
            "T04": [0, 0, 0],
            "T05": [0, 0, 1],
            "T06": [0, 0, 0],
            "T07": [0, 0, 0],
            "F1": [1, 0, 0],
            "F2": [0, 1, 1],
            "F3": [0, 0, 0],
            "F4": [0, 0, 0],
            "N_TRILHAS_NUCLEO": [1, 1, 1],
            "N_FAMILIAS_NUCLEO": [1, 1, 1],
            "T08_CONTEXTO": [0, 1, 0],
            "T09_CONTEXTO": [1, 0, 0],
        }
    )
    supplier = pd.DataFrame(
        {
            "CODIGO_UG": ["001", "001", "002"],
            "CHAVE_ENTIDADE": ["A", "B", "C"],
            "ANO": [2024, 2025, 2025],
            "N_COMPRAS_FORNECEDOR": [3, 2, 1],
            "VALOR_COMPRAS_FORNECEDOR": [600.0, 400.0, 200.0],
            "N_PORTADORES_FORNECEDOR": [1, 1, 1],
            "N_DIAS_COMPRA_FORNECEDOR": [2, 2, 1],
            "STATUS_PERIODO": ["COMPLETO", "COMPLETO", "COMPLETO"],
            "BANDA_EXPOSICAO_FORNECEDOR": ["B03_3_4", "B02_2", "B01_1"],
            "ROTULO_BANDA_EXPOSICAO_FORNECEDOR": ["3-4 compras", "2 compras", "1 compra"],
            "ORDEM_BANDA_EXPOSICAO_FORNECEDOR": [3, 2, 1],
            "T01": [1, 0, 0],
            "T02": [0, 0, 0],
            "T03": [0, 1, 0],
            "T04": [0, 0, 0],
            "T05": [0, 0, 1],
            "T06": [0, 0, 0],
            "F1": [1, 0, 0],
            "F2": [0, 1, 1],
            "F3": [0, 0, 0],
            "N_TRILHAS_ATIVAS": [1, 1, 1],
            "N_FAMILIAS_ATIVAS": [1, 1, 1],
            "T08_CONTEXTO": [0, 1, 0],
            "T09_CONTEXTO": [1, 0, 0],
        }
    )
    persist_serving_tables(
        {"matrix_ug_year": ug, "matrix_supplier_year": supplier},
        tmp_path,
    )
    repository = ServingRepository(tmp_path / "cpgf_serving.duckdb")
    return DashboardDataContext(repository=repository, bootstrap=SimpleNamespace(status="LOCAL"))


def test_dashboard_filter_rejects_inverted_years():
    with pytest.raises(ValueError):
        DashboardFilter(2025, 2024)


def test_overview_summary_uses_materialized_views(tmp_path):
    context = _context(tmp_path)
    summary = overview_summary(context, DashboardFilter(2024, 2025))

    assert summary["ugs"] == 2
    assert summary["operations"] == 25
    assert summary["total_value"] == 2450.0
    assert summary["suppliers"] == 3
    assert summary["signaled_ug_year"] == 3


def test_filters_are_applied_to_fixed_readonly_queries(tmp_path):
    context = _context(tmp_path)
    filters = DashboardFilter(2025, 2025, ("001",))

    annual = annual_overview(context, filters)
    assert annual["OPERACOES"].tolist() == [8]

    ranking = top_ugs(context, filters)
    assert ranking["CODIGO_UG"].tolist() == ["001"]


def test_trail_prevalence_includes_core_and_context_trails(tmp_path):
    context = _context(tmp_path)
    trails = trail_prevalence(context, DashboardFilter(2024, 2025))

    assert trails["CODIGO"].tolist() == [f"T{i:02d}" for i in range(1, 10)]
    assert int(trails.loc[trails["CODIGO"].eq("T01"), "UNIDADES_SINALIZADAS"].iloc[0]) == 1
    assert int(trails.loc[trails["CODIGO"].eq("T08"), "UNIDADES_SINALIZADAS"].iloc[0]) == 1
    assert trails.loc[trails["CODIGO"].eq("T08"), "TIPO"].iloc[0] == "Contexto"
