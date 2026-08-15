from __future__ import annotations

import re

import pandas as pd

from cpgf.dashboard.data import DashboardDataContext
from cpgf.geography.ug_dimension import UFS_BRASIL
from cpgf.serving.duckdb import open_catalog

_ALLOWED_REFERENCES = frozenset({"TRANSACAO", "EXTRATO"})
_SAFE_METRIC = re.compile(r"^[A-Z][A-Z0-9_]*$")


def _query(
    context: DashboardDataContext,
    sql: str,
    params: list[object] | None = None,
) -> pd.DataFrame:
    connection = open_catalog(context.repository.catalog_path)
    try:
        return connection.execute(sql, params or []).df()
    finally:
        connection.close()


def _validate_reference(reference: str) -> str:
    value = str(reference).strip().upper()
    if value not in _ALLOWED_REFERENCES:
        raise ValueError(f"Referência temporal não autorizada: {reference}.")
    return value


def _validate_metric(metric: str) -> str:
    value = str(metric).strip().upper()
    if not _SAFE_METRIC.fullmatch(value):
        raise ValueError(f"Métrica territorial inválida: {metric}.")
    return value


def geographic_metric_catalog(
    context: DashboardDataContext,
    *,
    reference: str | None = None,
) -> pd.DataFrame:
    """Lê o catálogo semântico materializado das métricas territoriais."""
    params: list[object] = []
    where = ""
    if reference is not None:
        where = "WHERE REFERENCIA_TEMPORAL = ?"
        params.append(_validate_reference(reference))
    return _query(
        context,
        f"""
        SELECT
            REFERENCIA_TEMPORAL,
            METRICA,
            ROTULO,
            UNIDADE,
            METRICA_PRINCIPAL
        FROM "v_geo_metric_catalog"
        {where}
        ORDER BY REFERENCIA_TEMPORAL, METRICA_PRINCIPAL DESC, ROTULO
        """,
        params,
    )


def geographic_available_years(
    context: DashboardDataContext,
    reference: str,
) -> list[int]:
    reference = _validate_reference(reference)
    frame = _query(
        context,
        """
        SELECT DISTINCT ANO
        FROM "v_geo_uf_ano_dashboard_long"
        WHERE REFERENCIA_TEMPORAL = ?
        ORDER BY ANO
        """,
        [reference],
    )
    return [int(value) for value in frame["ANO"].dropna().tolist()]


def geographic_uf_metric(
    context: DashboardDataContext,
    *,
    reference: str,
    year: int,
    metric: str,
) -> pd.DataFrame:
    """Lê uma métrica UF×ano já materializada, sem reconstruir o enriquecimento geográfico."""
    reference = _validate_reference(reference)
    metric = _validate_metric(metric)
    eligible = geographic_metric_catalog(context, reference=reference)
    if metric not in set(eligible["METRICA"].astype("string")):
        raise ValueError(f"Métrica {metric} não pertence à referência {reference}.")

    return _query(
        context,
        """
        SELECT
            ANO,
            UF,
            STATUS_PERIODO,
            REFERENCIA_TEMPORAL,
            METRICA,
            ROTULO_METRICA,
            UNIDADE,
            VALOR_METRICA
        FROM "v_geo_uf_ano_dashboard_long"
        WHERE REFERENCIA_TEMPORAL = ?
          AND ANO = ?
          AND METRICA = ?
        ORDER BY VALOR_METRICA DESC, UF
        """,
        [reference, int(year), metric],
    )


def territorial_ug_context(
    context: DashboardDataContext,
    *,
    uf: str,
    year: int,
    limit: int = 50,
) -> pd.DataFrame:
    """Contextualiza as UGs da UF selecionada usando a matriz UG-ano já materializada."""
    uf = str(uf).strip().upper()
    if uf not in UFS_BRASIL:
        raise ValueError(f"UF inválida: {uf}.")
    if not 1 <= int(limit) <= 500:
        raise ValueError("limit deve estar entre 1 e 500.")

    return _query(
        context,
        """
        SELECT
            d.UF_UG AS UF,
            m.ANO,
            m.CODIGO_UG,
            d.TITULO_UG_SIAFI,
            m.N_OPERACOES_EFETIVAS AS OPERACOES,
            m.VALOR_COMPRAS_UG,
            m.VALOR_SAQUES_UG,
            (m.VALOR_COMPRAS_UG + m.VALOR_SAQUES_UG) AS VALOR_TOTAL,
            m.N_TRILHAS_NUCLEO,
            m.N_FAMILIAS_NUCLEO,
            m.STATUS_PERIODO
        FROM "v_matrix_ug_year" AS m
        INNER JOIN "v_dim_ug_geografica" AS d
            ON d.UG_ID = m.CODIGO_UG
        WHERE d.UF_UG = ?
          AND m.ANO = ?
        ORDER BY
            m.N_TRILHAS_NUCLEO DESC,
            VALOR_TOTAL DESC,
            m.CODIGO_UG
        LIMIT ?
        """,
        [uf, int(year), int(limit)],
    )
