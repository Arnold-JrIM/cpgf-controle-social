from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest
from pydantic import ValidationError

from cpgf.ai import ToolName, ToolRequest, execute_tool, prepare_assistant_state, route_question
from cpgf.ai.contracts import QueryScope
from cpgf.ai.guardrails import (
    FreeSQLDisabledError,
    InputGuardrailError,
    OutputGuardrailError,
    reject_free_sql,
    validate_narrative,
    validate_question,
)
from cpgf.ai.router import Route
from cpgf.ai.tools import tool_catalog
from cpgf.dashboard.data import DashboardDataContext
from cpgf.serving import ServingRepository, persist_serving_tables
from cpgf.serving.distribution import ServingBootstrapResult


def _context(tmp_path: Path) -> DashboardDataContext:
    tables = {
        "matrix_ug_year": pd.DataFrame(
            {
                "ANO": [2025, 2025],
                "CODIGO_UG": ["000001", "000002"],
                "N_OPERACOES_EFETIVAS": [10, 5],
                "VALOR_COMPRAS_UG": [1000.0, 500.0],
                "VALOR_SAQUES_UG": [100.0, 0.0],
                "N_TRILHAS_NUCLEO": [2, 0],
                "N_FAMILIAS_NUCLEO": [1, 0],
                "N_COMPRAS_UG": [9, 5],
                "N_SAQUES_UG": [1, 0],
                "T01": [1, 0],
                "T02": [0, 0],
                "T03": [1, 0],
                "T04": [0, 0],
                "T05": [0, 0],
                "T06": [0, 0],
                "T07": [0, 0],
                "T08_CONTEXTO": [0, 0],
                "T09_CONTEXTO": [0, 0],
                "STATUS_PERIODO": ["COMPLETO", "COMPLETO"],
            }
        ),
        "matrix_supplier_year": pd.DataFrame(
            {
                "ANO": [2025],
                "CODIGO_UG": ["000001"],
                "CHAVE_ENTIDADE": ["fornecedor-a"],
                "N_COMPRAS_FORNECEDOR": [9],
                "VALOR_COMPRAS_FORNECEDOR": [1000.0],
                "N_TRILHAS_ATIVAS": [1],
            }
        ),
        "geo_metric_catalog": pd.DataFrame(
            {
                "REFERENCIA_TEMPORAL": ["TRANSACAO"],
                "METRICA": ["VALOR_TRANSACIONADO_OBSERVAVEL"],
                "ROTULO": ["Valor transacionado observável"],
                "UNIDADE": ["BRL"],
                "METRICA_PRINCIPAL": [True],
            }
        ),
        "geo_uf_ano_dashboard_long": pd.DataFrame(
            {
                "ANO": [2025, 2025],
                "UF": ["DF", "SP"],
                "STATUS_PERIODO": ["EXERCICIO_COMPLETO", "EXERCICIO_COMPLETO"],
                "REFERENCIA_TEMPORAL": ["TRANSACAO", "TRANSACAO"],
                "METRICA": ["VALOR_TRANSACIONADO_OBSERVAVEL"] * 2,
                "ROTULO_METRICA": ["Valor transacionado observável"] * 2,
                "UNIDADE": ["BRL", "BRL"],
                "VALOR_METRICA": [1000.0, 500.0],
            }
        ),
        "dim_ug_geografica": pd.DataFrame(
            {
                "UG_ID": ["000001", "000002"],
                "UF_UG": ["DF", "SP"],
                "TITULO_UG_SIAFI": ["UG A", "UG B"],
            }
        ),
    }
    persist_serving_tables(tables, tmp_path)
    catalog = tmp_path / "cpgf_serving.duckdb"
    bootstrap = ServingBootstrapResult(
        status="LOCAL_VALID",
        bundle_dir=tmp_path,
        catalog_path=catalog,
        source_url=None,
        validation={"status": "PASS"},
    )
    return DashboardDataContext(repository=ServingRepository(catalog), bootstrap=bootstrap)


def test_question_guardrail_blocks_explicit_mutation_and_accepts_analysis():
    assert validate_question("Quais UGs têm sinais em 2025?")
    with pytest.raises(InputGuardrailError):
        validate_question("DELETE FROM matrix_ug_year")
    with pytest.raises(InputGuardrailError):
        validate_question("recalcule T01 com outro limiar")


def test_free_sql_is_unconditionally_disabled():
    with pytest.raises(FreeSQLDisabledError):
        reject_free_sql("SELECT * FROM v_matrix_ug_year")


def test_output_guardrail_rejects_categorical_accusation():
    assert validate_narrative("O registro apresenta um sinal que merece verificação.")
    with pytest.raises(OutputGuardrailError):
        validate_narrative("A Unidade Gestora é fraude.")


def test_contract_rejects_invalid_scope_and_extra_arguments():
    with pytest.raises(ValidationError):
        QueryScope(year_start=2026, year_end=2025)
    with pytest.raises(ValidationError):
        QueryScope(year_start=2025, year_end=2025, ug_codes=("123",))


def test_router_is_deterministic_and_does_not_call_llm():
    assert route_question("Mostre o mapa por estado").route == Route.TERRITORIAL
    state = prepare_assistant_state("Explique a metodologia das trilhas")
    assert state.route == Route.METHODOLOGY
    assert state.llm_called is False
    assert state.tool_request is None


def test_registry_has_no_sql_or_rag_tool():
    names = {item["name"] for item in tool_catalog()}
    assert "sql" not in names
    assert "rag" not in names
    assert names == {item.value for item in ToolName}


def test_registered_tools_read_materialized_fixture(tmp_path):
    context = _context(tmp_path)
    overview = execute_tool(
        context,
        ToolRequest(
            tool=ToolName.OVERVIEW,
            arguments={"year_start": 2025, "year_end": 2025},
        ),
    )
    assert overview.summary["ugs"] == 2
    assert overview.summary["operations"] == 15
    assert overview.provenance.read_only is True

    trails = execute_tool(
        context,
        ToolRequest(
            tool=ToolName.TRAIL_PREVALENCE,
            arguments={"year_start": 2025, "year_end": 2025},
        ),
    )
    assert len(trails.records) == 9

    territorial = execute_tool(
        context,
        ToolRequest(
            tool=ToolName.TERRITORIAL_METRIC,
            arguments={
                "reference": "TRANSACAO",
                "year": 2025,
                "metric": "VALOR_TRANSACIONADO_OBSERVAVEL",
            },
        ),
    )
    assert territorial.summary["ufs"] == 2
    assert sum(row["VALOR_METRICA"] for row in territorial.records) == 1500.0


def test_tool_arguments_do_not_accept_sql_field(tmp_path):
    context = _context(tmp_path)
    with pytest.raises(ValidationError):
        execute_tool(
            context,
            ToolRequest(
                tool=ToolName.OVERVIEW,
                arguments={
                    "year_start": 2025,
                    "year_end": 2025,
                    "sql": "SELECT 1",
                },
            ),
        )
