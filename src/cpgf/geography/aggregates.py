from __future__ import annotations

import math

import pandas as pd

from .enrichment import build_geographic_projection

_COMPLETE_START = 2013
_COMPLETE_END = 2025

TRANSACAO_METRICS = (
    ("VALOR_TRANSACIONADO_OBSERVAVEL", "Valor transacionado observável", "BRL"),
    ("PARTICIPACAO_NACIONAL_PCT", "Participação nacional", "PERCENTUAL"),
    ("VALOR_MEDIO_POR_UG", "Valor médio por UG", "BRL"),
    ("N_TRANSACOES_OBSERVAVEIS", "Quantidade de transações observáveis", "CONTAGEM"),
    ("N_UG_COM_MOVIMENTACAO", "UGs com movimentação", "CONTAGEM"),
    ("VALOR_COMPRAS_OBSERVAVEIS", "Compras observáveis", "BRL"),
    ("VALOR_SAQUES_OBSERVAVEIS", "Saques observáveis", "BRL"),
)
EXTRATO_METRICS = (
    ("VALOR_TOTAL_REGISTRADO", "Valor total registrado", "BRL"),
    ("PARTICIPACAO_NACIONAL_PCT", "Participação nacional", "PERCENTUAL"),
    ("VALOR_MEDIO_POR_UG", "Valor médio por UG", "BRL"),
    ("N_REGISTROS", "Quantidade de registros", "CONTAGEM"),
    ("N_UG_COM_MOVIMENTACAO", "UGs com movimentação", "CONTAGEM"),
    ("VALOR_SIGILOSO", "Valor sob sigilo", "BRL"),
    ("PCT_SIGILO_VALOR", "Percentual do valor sob sigilo", "PERCENTUAL"),
    (
        "VALOR_COM_DATA_TRANSACAO_OBSERVAVEL",
        "Valor com data da transação observável",
        "BRL",
    ),
    ("TAXA_OBSERVABILIDADE_VALOR", "Observabilidade do valor", "PERCENTUAL"),
    ("TAXA_OBSERVABILIDADE_REGISTROS", "Observabilidade dos registros", "PERCENTUAL"),
)


def _status(year: pd.Series) -> pd.Series:
    return pd.Series(
        [
            "EXERCICIO_COMPLETO"
            if _COMPLETE_START <= int(value) <= _COMPLETE_END
            else "PERIODO_PARCIAL"
            for value in year
        ],
        index=year.index,
        dtype="string",
    )


def _reais(cents: pd.Series) -> pd.Series:
    return cents.astype("Float64") / 100.0


def _safe_percent(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    den = denominator.astype("Float64").replace(0, pd.NA)
    return numerator.astype("Float64") / den * 100.0


def _aggregate_transaction(geo: pd.DataFrame) -> pd.DataFrame:
    base = geo.loc[
        geo["GEO_UF_BRASIL"]
        & geo["GEO_DATA_TRANSACAO_OBSERVAVEL"]
        & geo["GEO_POSITIVA_NAO_AJUSTE"]
    ].copy()
    base["ANO"] = base["ANO_TRANSACAO"].astype("Int64")
    base["CENTAVOS_COMPRAS"] = base["VALOR_CENTAVOS"].where(base["GEO_COMPRA_OBSERVAVEL"], 0)
    base["CENTAVOS_SAQUES"] = base["VALOR_CENTAVOS"].where(base["GEO_SAQUE_OBSERVAVEL"], 0)
    grouped = base.groupby(["ANO", "UF_UG"], as_index=False, observed=True).agg(
        VALOR_CENTAVOS=("VALOR_CENTAVOS", "sum"),
        N_TRANSACOES_OBSERVAVEIS=("UG_ID", "size"),
        N_UG_COM_MOVIMENTACAO=("UG_ID", "nunique"),
        CENTAVOS_COMPRAS=("CENTAVOS_COMPRAS", "sum"),
        CENTAVOS_SAQUES=("CENTAVOS_SAQUES", "sum"),
    )
    grouped = grouped.rename(columns={"UF_UG": "UF"})
    grouped["VALOR_TRANSACIONADO_OBSERVAVEL"] = _reais(grouped["VALOR_CENTAVOS"])
    grouped["VALOR_COMPRAS_OBSERVAVEIS"] = _reais(grouped["CENTAVOS_COMPRAS"])
    grouped["VALOR_SAQUES_OBSERVAVEIS"] = _reais(grouped["CENTAVOS_SAQUES"])
    grouped["VALOR_MEDIO_POR_UG"] = (
        grouped["VALOR_TRANSACIONADO_OBSERVAVEL"] / grouped["N_UG_COM_MOVIMENTACAO"]
    )
    national = grouped.groupby("ANO")["VALOR_TRANSACIONADO_OBSERVAVEL"].transform("sum")
    grouped["PARTICIPACAO_NACIONAL_PCT"] = _safe_percent(
        grouped["VALOR_TRANSACIONADO_OBSERVAVEL"], national
    )
    grouped["STATUS_PERIODO"] = _status(grouped["ANO"])
    columns = [
        "ANO", "UF", "STATUS_PERIODO", "VALOR_TRANSACIONADO_OBSERVAVEL",
        "PARTICIPACAO_NACIONAL_PCT", "VALOR_MEDIO_POR_UG", "N_TRANSACOES_OBSERVAVEIS",
        "N_UG_COM_MOVIMENTACAO", "VALOR_COMPRAS_OBSERVAVEIS", "VALOR_SAQUES_OBSERVAVEIS",
    ]
    return grouped[columns].sort_values(["ANO", "UF"], kind="stable").reset_index(drop=True)


def _aggregate_extract(geo: pd.DataFrame) -> pd.DataFrame:
    base = geo.loc[geo["GEO_UF_BRASIL"] & geo["GEO_POSITIVA_NAO_AJUSTE"]].copy()
    base = base.loc[base["ANO_EXTRATO_REF"].notna()].copy()
    base["ANO"] = base["ANO_EXTRATO_REF"].astype("Int64")
    base["CENTAVOS_DATA"] = base["VALOR_CENTAVOS"].where(base["GEO_DATA_TRANSACAO_OBSERVAVEL"], 0)
    base["CENTAVOS_SIGILO"] = base["VALOR_CENTAVOS"].where(base["GEO_SIGILOSO"], 0)
    base["CENTAVOS_COMPRAS"] = base["VALOR_CENTAVOS"].where(base["GEO_COMPRA_OBSERVAVEL"], 0)
    base["CENTAVOS_SAQUES"] = base["VALOR_CENTAVOS"].where(base["GEO_SAQUE_OBSERVAVEL"], 0)
    base["REGISTRO_COM_DATA"] = base["GEO_DATA_TRANSACAO_OBSERVAVEL"].astype("int64")
    base["REGISTRO_SIGILOSO"] = base["GEO_SIGILOSO"].astype("int64")
    grouped = base.groupby(["ANO", "UF_UG"], as_index=False, observed=True).agg(
        VALOR_CENTAVOS=("VALOR_CENTAVOS", "sum"),
        N_REGISTROS=("UG_ID", "size"),
        N_UG_COM_MOVIMENTACAO=("UG_ID", "nunique"),
        CENTAVOS_DATA=("CENTAVOS_DATA", "sum"),
        N_REGISTROS_COM_DATA_TRANSACAO=("REGISTRO_COM_DATA", "sum"),
        CENTAVOS_SIGILO=("CENTAVOS_SIGILO", "sum"),
        N_REGISTROS_SIGILOSOS=("REGISTRO_SIGILOSO", "sum"),
        CENTAVOS_COMPRAS=("CENTAVOS_COMPRAS", "sum"),
        CENTAVOS_SAQUES=("CENTAVOS_SAQUES", "sum"),
    )
    grouped = grouped.rename(columns={"UF_UG": "UF"})
    grouped["VALOR_TOTAL_REGISTRADO"] = _reais(grouped["VALOR_CENTAVOS"])
    grouped["VALOR_COM_DATA_TRANSACAO_OBSERVAVEL"] = _reais(grouped["CENTAVOS_DATA"])
    grouped["VALOR_SIGILOSO"] = _reais(grouped["CENTAVOS_SIGILO"])
    grouped["VALOR_COMPRAS_OBSERVAVEIS"] = _reais(grouped["CENTAVOS_COMPRAS"])
    grouped["VALOR_SAQUES_OBSERVAVEIS"] = _reais(grouped["CENTAVOS_SAQUES"])
    grouped["VALOR_MEDIO_POR_UG"] = (
        grouped["VALOR_TOTAL_REGISTRADO"] / grouped["N_UG_COM_MOVIMENTACAO"]
    )
    national = grouped.groupby("ANO")["VALOR_TOTAL_REGISTRADO"].transform("sum")
    grouped["PARTICIPACAO_NACIONAL_PCT"] = _safe_percent(
        grouped["VALOR_TOTAL_REGISTRADO"], national
    )
    grouped["PCT_SIGILO_VALOR"] = _safe_percent(
        grouped["VALOR_SIGILOSO"], grouped["VALOR_TOTAL_REGISTRADO"]
    )
    grouped["TAXA_OBSERVABILIDADE_VALOR"] = _safe_percent(
        grouped["VALOR_COM_DATA_TRANSACAO_OBSERVAVEL"], grouped["VALOR_TOTAL_REGISTRADO"]
    )
    grouped["TAXA_OBSERVABILIDADE_REGISTROS"] = _safe_percent(
        grouped["N_REGISTROS_COM_DATA_TRANSACAO"], grouped["N_REGISTROS"]
    )
    grouped["STATUS_PERIODO"] = _status(grouped["ANO"])
    columns = [
        "ANO", "UF", "STATUS_PERIODO", "VALOR_TOTAL_REGISTRADO", "PARTICIPACAO_NACIONAL_PCT",
        "VALOR_MEDIO_POR_UG", "N_REGISTROS", "N_UG_COM_MOVIMENTACAO", "VALOR_SIGILOSO",
        "PCT_SIGILO_VALOR", "VALOR_COM_DATA_TRANSACAO_OBSERVAVEL", "N_REGISTROS_COM_DATA_TRANSACAO",
        "N_REGISTROS_SIGILOSOS", "TAXA_OBSERVABILIDADE_VALOR", "TAXA_OBSERVABILIDADE_REGISTROS",
        "VALOR_COMPRAS_OBSERVAVEIS", "VALOR_SAQUES_OBSERVAVEIS",
    ]
    return grouped[columns].sort_values(["ANO", "UF"], kind="stable").reset_index(drop=True)


def metric_catalog() -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for reference, metrics in (("TRANSACAO", TRANSACAO_METRICS), ("EXTRATO", EXTRATO_METRICS)):
        for metric, label, unit in metrics:
            rows.append(
                {
                    "REFERENCIA_TEMPORAL": reference,
                    "METRICA": metric,
                    "ROTULO": label,
                    "UNIDADE": unit,
                    "METRICA_PRINCIPAL": metric
                    == (
                        "VALOR_TRANSACIONADO_OBSERVAVEL"
                        if reference == "TRANSACAO"
                        else "VALOR_TOTAL_REGISTRADO"
                    ),
                }
            )
    return pd.DataFrame(rows)


def _long(
    frame: pd.DataFrame,
    reference: str,
    metrics: tuple[tuple[str, str, str], ...],
) -> pd.DataFrame:
    parts = []
    for metric, label, unit in metrics:
        part = frame[["ANO", "UF", "STATUS_PERIODO", metric]].copy()
        part = part.rename(columns={metric: "VALOR_METRICA"})
        part["REFERENCIA_TEMPORAL"] = reference
        part["METRICA"] = metric
        part["ROTULO_METRICA"] = label
        part["UNIDADE"] = unit
        parts.append(part)
    return pd.concat(parts, ignore_index=True)


def build_geographic_aggregates(
    staged: pd.DataFrame,
    dimension: pd.DataFrame,
) -> dict[str, pd.DataFrame]:
    geo = build_geographic_projection(staged, dimension)
    transaction = _aggregate_transaction(geo)
    extract = _aggregate_extract(geo)
    dashboard = pd.concat(
        [
            _long(transaction, "TRANSACAO", TRANSACAO_METRICS),
            _long(extract, "EXTRATO", EXTRATO_METRICS),
        ],
        ignore_index=True,
    ).sort_values(
        ["REFERENCIA_TEMPORAL", "ANO", "UF", "METRICA"],
        kind="stable",
    ).reset_index(drop=True)
    return {
        "geo_uf_ano_transacao": transaction,
        "geo_uf_ano_extrato": extract,
        "geo_uf_ano_dashboard_long": dashboard,
        "geo_metric_catalog": metric_catalog(),
    }


def validate_geographic_baseline(tables: dict[str, pd.DataFrame]) -> dict[str, object]:
    transaction = tables["geo_uf_ano_transacao"]
    extract = tables["geo_uf_ano_extrato"]
    dashboard = tables["geo_uf_ano_dashboard_long"]
    catalog = tables["geo_metric_catalog"]
    checks = {
        "transaction_rows": int(len(transaction)),
        "extract_rows": int(len(extract)),
        "dashboard_rows": int(len(dashboard)),
        "metric_count": int(len(catalog)),
        "transaction_value": float(transaction["VALOR_TRANSACIONADO_OBSERVAVEL"].sum()),
        "transaction_records": int(transaction["N_TRANSACOES_OBSERVAVEIS"].sum()),
        "extract_value": float(extract["VALOR_TOTAL_REGISTRADO"].sum()),
        "extract_records": int(extract["N_REGISTROS"].sum()),
        "observable_value": float(extract["VALOR_COM_DATA_TRANSACAO_OBSERVAVEL"].sum()),
        "sigilous_value": float(extract["VALOR_SIGILOSO"].sum()),
        "observable_records": int(extract["N_REGISTROS_COM_DATA_TRANSACAO"].sum()),
        "sigilous_records": int(extract["N_REGISTROS_SIGILOSOS"].sum()),
    }
    expected = {
        "transaction_rows": 405,
        "extract_rows": 378,
        "dashboard_rows": 6_615,
        "metric_count": 17,
        "transaction_records": 1_506_714,
        "extract_records": 1_876_065,
        "observable_records": 1_506_714,
        "sigilous_records": 369_355,
    }
    for key, value in expected.items():
        if checks[key] != value:
            raise ValueError(
                f"Baseline Geo 1.1.0 divergente em {key}: esperado={value}; obtido={checks[key]}."
            )
    expected_money = {
        "transaction_value": 506_719_563.42,
        "extract_value": 976_936_749.90,
        "observable_value": 506_719_563.42,
        "sigilous_value": 470_219_284.18,
    }
    for key, value in expected_money.items():
        if not math.isclose(checks[key], value, abs_tol=0.01):
            raise ValueError(
                f"Baseline Geo 1.1.0 divergente em {key}: esperado={value}; obtido={checks[key]}."
            )
    return checks
