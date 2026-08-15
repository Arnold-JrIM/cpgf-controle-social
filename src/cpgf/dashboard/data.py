from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import pandas as pd

from cpgf.serving.distribution import (
    ServingBootstrapResult,
    ServingDistributionConfig,
    ServingUnavailableError,
    bootstrap_serving,
)
from cpgf.serving.duckdb import open_catalog
from cpgf.serving.repository import ServingRepository

TRAIL_LABELS: dict[str, str] = {
    "T01": "Despesa realizada em final de semana",
    "T02": "Compra parcelada",
    "T03": "Repetição exata",
    "T04": "Repetição multiportador",
    "T05": "Recorrência de aquisições",
    "T06": "Concentração em fornecedor",
    "T07": "Saques sucessivos",
    "T08": "Lei de Benford",
    "T09": "Proximidade a limites financeiros",
}

UG_CORE_TRAILS: tuple[str, ...] = ("T01", "T02", "T03", "T04", "T05", "T06", "T07")
SUPPLIER_CORE_TRAILS: tuple[str, ...] = ("T01", "T02", "T03", "T04", "T05", "T06")


@dataclass(frozen=True)
class DashboardDataContext:
    repository: ServingRepository
    bootstrap: ServingBootstrapResult


@dataclass(frozen=True)
class DashboardFilter:
    year_start: int
    year_end: int
    ug_codes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if int(self.year_start) > int(self.year_end):
            raise ValueError("year_start não pode ser posterior a year_end.")


def load_dashboard_data(
    *,
    bundle_dir: Path | None = None,
    offline: bool | None = None,
    force_download: bool = False,
) -> DashboardDataContext:
    """Inicializa a camada de leitura sem executar preparação, trilhas ou governança."""
    config = ServingDistributionConfig.from_env()
    if bundle_dir is not None or offline is not None:
        config = ServingDistributionConfig(
            bundle_dir=Path(bundle_dir) if bundle_dir is not None else config.bundle_dir,
            cache_dir=config.cache_dir,
            source_url=config.source_url,
            checksum_url=config.checksum_url,
            offline=config.offline if offline is None else bool(offline),
        )

    bootstrap = bootstrap_serving(config, force_download=force_download)
    repository = ServingRepository(bootstrap.catalog_path)
    return DashboardDataContext(repository=repository, bootstrap=bootstrap)


def serving_health(
    *,
    bundle_dir: Path | None = None,
    offline: bool | None = None,
) -> dict[str, object]:
    """Retorna estado simples para a interface sem propagar falha de distribuição."""
    try:
        context = load_dashboard_data(bundle_dir=bundle_dir, offline=offline)
    except ServingUnavailableError as exc:
        return {
            "status": "UNAVAILABLE",
            "message": str(exc),
            "tables": 0,
            "source": None,
        }

    views = context.repository.list_views()
    return {
        "status": "READY",
        "message": "Serving 1.4.0 íntegro e disponível para consulta read-only.",
        "tables": len(views),
        "source": context.bootstrap.status,
        "catalog": str(context.bootstrap.catalog_path),
    }


def _normalized_ugs(values: Iterable[str]) -> tuple[str, ...]:
    cleaned = tuple(dict.fromkeys(str(value).strip() for value in values if str(value).strip()))
    return cleaned


def _where(filters: DashboardFilter, *, alias: str | None = None) -> tuple[str, list[object]]:
    prefix = f"{alias}." if alias else ""
    clauses = [f"{prefix}ANO BETWEEN ? AND ?"]
    params: list[object] = [int(filters.year_start), int(filters.year_end)]
    ug_codes = _normalized_ugs(filters.ug_codes)
    if ug_codes:
        placeholders = ", ".join("?" for _ in ug_codes)
        clauses.append(f"{prefix}CODIGO_UG IN ({placeholders})")
        params.extend(ug_codes)
    return " AND ".join(clauses), params


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


def available_years(context: DashboardDataContext) -> list[int]:
    frame = _query(
        context,
        'SELECT DISTINCT ANO FROM "v_matrix_ug_year" ORDER BY ANO',
    )
    return [int(value) for value in frame["ANO"].dropna().tolist()]


def overview_summary(
    context: DashboardDataContext,
    filters: DashboardFilter,
) -> dict[str, float | int]:
    where, params = _where(filters)
    ug = _query(
        context,
        f"""
        SELECT
            COUNT(*) AS UG_ANO,
            COUNT(DISTINCT CODIGO_UG) AS UGS,
            COALESCE(SUM(N_OPERACOES_EFETIVAS), 0) AS OPERACOES,
            COALESCE(SUM(VALOR_COMPRAS_UG + VALOR_SAQUES_UG), 0) AS VALOR_TOTAL,
            COALESCE(SUM(CASE WHEN N_TRILHAS_NUCLEO > 0 THEN 1 ELSE 0 END), 0)
                AS UG_ANO_SINALIZADAS,
            COALESCE(SUM(N_COMPRAS_UG), 0) AS COMPRAS,
            COALESCE(SUM(N_SAQUES_UG), 0) AS SAQUES
        FROM "v_matrix_ug_year"
        WHERE {where}
        """,
        params,
    ).iloc[0]

    supplier_where, supplier_params = _where(filters)
    supplier = _query(
        context,
        f"""
        SELECT
            COUNT(DISTINCT CHAVE_ENTIDADE) AS FORNECEDORES,
            COUNT(*) AS FORNECEDOR_ANO,
            COALESCE(SUM(CASE WHEN N_TRILHAS_ATIVAS > 0 THEN 1 ELSE 0 END), 0)
                AS FORNECEDOR_ANO_SINALIZADOS
        FROM "v_matrix_supplier_year"
        WHERE {supplier_where}
        """,
        supplier_params,
    ).iloc[0]

    return {
        "ug_year": int(ug["UG_ANO"]),
        "ugs": int(ug["UGS"]),
        "operations": int(ug["OPERACOES"]),
        "total_value": float(ug["VALOR_TOTAL"]),
        "signaled_ug_year": int(ug["UG_ANO_SINALIZADAS"]),
        "purchases": int(ug["COMPRAS"]),
        "withdrawals": int(ug["SAQUES"]),
        "suppliers": int(supplier["FORNECEDORES"]),
        "supplier_year": int(supplier["FORNECEDOR_ANO"]),
        "signaled_supplier_year": int(supplier["FORNECEDOR_ANO_SINALIZADOS"]),
    }


def annual_overview(
    context: DashboardDataContext,
    filters: DashboardFilter,
) -> pd.DataFrame:
    where, params = _where(filters)
    return _query(
        context,
        f"""
        SELECT
            ANO,
            COUNT(DISTINCT CODIGO_UG) AS UGS,
            SUM(N_OPERACOES_EFETIVAS) AS OPERACOES,
            SUM(VALOR_COMPRAS_UG) AS VALOR_COMPRAS,
            SUM(VALOR_SAQUES_UG) AS VALOR_SAQUES,
            SUM(VALOR_COMPRAS_UG + VALOR_SAQUES_UG) AS VALOR_TOTAL,
            SUM(CASE WHEN N_TRILHAS_NUCLEO > 0 THEN 1 ELSE 0 END) AS UG_ANO_SINALIZADAS
        FROM "v_matrix_ug_year"
        WHERE {where}
        GROUP BY ANO
        ORDER BY ANO
        """,
        params,
    )


def trail_prevalence(
    context: DashboardDataContext,
    filters: DashboardFilter,
) -> pd.DataFrame:
    where, params = _where(filters)
    expressions = [f'SUM("{trail}") AS "{trail}"' for trail in UG_CORE_TRAILS]
    expressions.extend(
        [
            'SUM("T08_CONTEXTO") AS "T08"',
            'SUM("T09_CONTEXTO") AS "T09"',
        ]
    )
    select_flags = ",\n            ".join(expressions)
    row = _query(
        context,
        f"""
        SELECT
            COUNT(*) AS N_UNIDADES,
            {select_flags}
        FROM "v_matrix_ug_year"
        WHERE {where}
        """,
        params,
    ).iloc[0]
    universe = int(row["N_UNIDADES"])
    records = []
    for code in TRAIL_LABELS:
        count = 0 if pd.isna(row[code]) else int(row[code])
        records.append(
            {
                "CODIGO": code,
                "TRILHA": TRAIL_LABELS[code],
                "TIPO": "Núcleo" if code in UG_CORE_TRAILS else "Contexto",
                "UNIDADES_SINALIZADAS": count,
                "PREVALENCIA": (count / universe) if universe else 0.0,
                "N_UNIVERSO": universe,
            }
        )
    return pd.DataFrame(records)


def top_ugs(
    context: DashboardDataContext,
    filters: DashboardFilter,
    *,
    limit: int = 20,
) -> pd.DataFrame:
    where, params = _where(filters)
    params = [*params, int(limit)]
    return _query(
        context,
        f"""
        SELECT
            CODIGO_UG,
            COUNT(*) AS ANOS_OBSERVADOS,
            SUM(N_OPERACOES_EFETIVAS) AS OPERACOES,
            SUM(VALOR_COMPRAS_UG + VALOR_SAQUES_UG) AS VALOR_TOTAL,
            SUM(CASE WHEN N_TRILHAS_NUCLEO > 0 THEN 1 ELSE 0 END) AS ANOS_COM_SINAL,
            SUM(N_TRILHAS_NUCLEO) AS SOMA_TRILHAS_ATIVAS
        FROM "v_matrix_ug_year"
        WHERE {where}
        GROUP BY CODIGO_UG
        ORDER BY ANOS_COM_SINAL DESC, SOMA_TRILHAS_ATIVAS DESC, VALOR_TOTAL DESC
        LIMIT ?
        """,
        params,
    )


def top_suppliers(
    context: DashboardDataContext,
    filters: DashboardFilter,
    *,
    limit: int = 20,
) -> pd.DataFrame:
    where, params = _where(filters)
    params = [*params, int(limit)]
    return _query(
        context,
        f"""
        SELECT
            CHAVE_ENTIDADE,
            COUNT(DISTINCT CODIGO_UG) AS UGS,
            COUNT(DISTINCT ANO) AS ANOS_OBSERVADOS,
            SUM(N_COMPRAS_FORNECEDOR) AS COMPRAS,
            SUM(VALOR_COMPRAS_FORNECEDOR) AS VALOR_COMPRAS,
            SUM(CASE WHEN N_TRILHAS_ATIVAS > 0 THEN 1 ELSE 0 END)
                AS UNIDADES_ANO_COM_SINAL,
            SUM(N_TRILHAS_ATIVAS) AS SOMA_TRILHAS_ATIVAS
        FROM "v_matrix_supplier_year"
        WHERE {where}
        GROUP BY CHAVE_ENTIDADE
        HAVING SUM(CASE WHEN N_TRILHAS_ATIVAS > 0 THEN 1 ELSE 0 END) > 0
        ORDER BY UNIDADES_ANO_COM_SINAL DESC, SOMA_TRILHAS_ATIVAS DESC, VALOR_COMPRAS DESC
        LIMIT ?
        """,
        params,
    )


def ug_signal_distribution(
    context: DashboardDataContext,
    filters: DashboardFilter,
) -> pd.DataFrame:
    where, params = _where(filters)
    return _query(
        context,
        f"""
        SELECT
            N_TRILHAS_NUCLEO AS N_TRILHAS,
            COUNT(*) AS UNIDADES
        FROM "v_matrix_ug_year"
        WHERE {where}
        GROUP BY N_TRILHAS_NUCLEO
        ORDER BY N_TRILHAS_NUCLEO
        """,
        params,
    )


def ug_exposure_distribution(
    context: DashboardDataContext,
    filters: DashboardFilter,
) -> pd.DataFrame:
    where, params = _where(filters)
    return _query(
        context,
        f"""
        SELECT
            DECIL_EXPOSICAO_ANUAL AS DECIL,
            COUNT(*) AS UG_ANO,
            SUM(N_OPERACOES_EFETIVAS) AS OPERACOES,
            SUM(VALOR_COMPRAS_UG + VALOR_SAQUES_UG) AS VALOR_TOTAL,
            SUM(CASE WHEN N_TRILHAS_NUCLEO > 0 THEN 1 ELSE 0 END) AS UG_ANO_SINALIZADAS
        FROM "v_matrix_ug_year"
        WHERE {where}
        GROUP BY DECIL_EXPOSICAO_ANUAL
        ORDER BY DECIL_EXPOSICAO_ANUAL
        """,
        params,
    )


def supplier_exposure_distribution(
    context: DashboardDataContext,
    filters: DashboardFilter,
) -> pd.DataFrame:
    where, params = _where(filters)
    return _query(
        context,
        f"""
        SELECT
            ORDEM_BANDA_EXPOSICAO_FORNECEDOR AS ORDEM,
            ROTULO_BANDA_EXPOSICAO_FORNECEDOR AS BANDA,
            COUNT(*) AS UNIDADES,
            SUM(VALOR_COMPRAS_FORNECEDOR) AS VALOR_COMPRAS,
            SUM(CASE WHEN N_TRILHAS_ATIVAS > 0 THEN 1 ELSE 0 END) AS UNIDADES_SINALIZADAS
        FROM "v_matrix_supplier_year"
        WHERE {where}
        GROUP BY ORDEM_BANDA_EXPOSICAO_FORNECEDOR, ROTULO_BANDA_EXPOSICAO_FORNECEDOR
        ORDER BY ORDEM_BANDA_EXPOSICAO_FORNECEDOR
        """,
        params,
    )


def diagnostic_table(
    context: DashboardDataContext,
    logical_name: str,
    *,
    limit: int = 10_000,
) -> pd.DataFrame:
    if not logical_name.startswith(
        ("overlap_", "marginal_", "multicollinearity_", "pca_")
    ):
        raise ValueError("Apenas tabelas diagnósticas autorizadas podem ser exibidas.")
    return context.repository.read(logical_name, limit=limit)
