from __future__ import annotations

from decimal import ROUND_HALF_EVEN, Decimal

import pandas as pd

from .base import ensure_transaction_ids, keyed_signal_id_md5, require_columns

T09_NEAR_LOWER = 0.90
T09_MODE = "CENARIOS_PARALELOS_SEM_CATEGORIA"
T09_LEGAL_APPLICABILITY = "NAO_CONCLUSIVA_SEM_OBJETO_CATEGORIA"

_T09_PERIODS = (
    ("2002-04-23", "2018-07-18", "Portaria MF 95/2002 + Lei 8.666/1993", "COMPRAS_SERVICOS", "80000.00", "0.10", "0.01", "art. 23, II, a"),
    ("2002-04-23", "2018-07-18", "Portaria MF 95/2002 + Lei 8.666/1993", "OBRAS_ENGENHARIA", "150000.00", "0.10", "0.01", "art. 23, I, a"),
    ("2018-07-19", "2023-11-30", "Portaria MF 95/2002 + Decreto 9.412/2018", "COMPRAS_SERVICOS", "176000.00", "0.10", "0.01", "art. 23, II, a"),
    ("2018-07-19", "2023-11-30", "Portaria MF 95/2002 + Decreto 9.412/2018", "OBRAS_ENGENHARIA", "330000.00", "0.10", "0.01", "art. 23, I, a"),
    ("2023-12-01", "2023-12-31", "Portaria Normativa MF 1.344/2023 + Decreto 11.317/2022", "COMPRAS_SERVICOS", "57208.33", "0.50", "0.05", "art. 75, II"),
    ("2023-12-01", "2023-12-31", "Portaria Normativa MF 1.344/2023 + Decreto 11.317/2022", "OBRAS_ENGENHARIA", "114416.65", "0.50", "0.05", "art. 75, I"),
    ("2024-01-01", "2024-12-31", "Portaria Normativa MF 1.344/2023 + Decreto 11.871/2023", "COMPRAS_SERVICOS", "59906.02", "0.50", "0.05", "art. 75, II"),
    ("2024-01-01", "2024-12-31", "Portaria Normativa MF 1.344/2023 + Decreto 11.871/2023", "OBRAS_ENGENHARIA", "119812.02", "0.50", "0.05", "art. 75, I"),
    ("2025-01-01", "2025-12-31", "Portaria Normativa MF 1.344/2023 + Decreto 12.343/2024", "COMPRAS_SERVICOS", "62725.59", "0.50", "0.05", "art. 75, II"),
    ("2025-01-01", "2025-12-31", "Portaria Normativa MF 1.344/2023 + Decreto 12.343/2024", "OBRAS_ENGENHARIA", "125451.15", "0.50", "0.05", "art. 75, I"),
    ("2026-01-01", "2026-12-31", "Portaria Normativa MF 1.344/2023 + Decreto 12.807/2025", "COMPRAS_SERVICOS", "65492.11", "0.50", "0.05", "art. 75, II"),
    ("2026-01-01", "2026-12-31", "Portaria Normativa MF 1.344/2023 + Decreto 12.807/2025", "OBRAS_ENGENHARIA", "130984.20", "0.50", "0.05", "art. 75, I"),
)


def _round_money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN)


def build_normative_dimension() -> pd.DataFrame:
    """Constrói a dimensão temporal congelada de referências T09."""
    rows: list[dict[str, object]] = []
    for start, end, norm, category, reference, pct_grant, pct_small, device in _T09_PERIODS:
        reference_dec = Decimal(reference)
        pct_grant_dec = Decimal(pct_grant)
        pct_small_dec = Decimal(pct_small)
        grant = _round_money(reference_dec * pct_grant_dec)
        small = _round_money(reference_dec * pct_small_dec)
        rows.append(
            {
                "VIGENCIA_INICIO": pd.Timestamp(start),
                "VIGENCIA_FIM": pd.Timestamp(end),
                "NORMA_REFERENCIA": norm,
                "CATEGORIA_CENARIO": category,
                "DISPOSITIVO_REFERENCIA": device,
                "VALOR_BASE_REFERENCIA": float(reference_dec),
                "PERCENTUAL_CONCESSAO_CPGF": float(pct_grant_dec),
                "PERCENTUAL_PEQUENO_VULTO_CPGF": float(pct_small_dec),
                "LIMITE_CONCESSAO_CPGF": float(grant),
                "LIMITE_PEQUENO_VULTO_CPGF": float(small),
                "LIMITE_CONCESSAO_CENTAVOS": int(grant * 100),
                "LIMITE_PEQUENO_VULTO_CENTAVOS": int(small * 100),
                "APLICABILIDADE": "CENARIO_NAO_CLASSIFICADO_PELA_BASE_PUBLICA",
            }
        )
    return pd.DataFrame(rows)


def classify_scenario(value_cents: int, limit_cents: int) -> str:
    """Classifica um valor contra uma referência em centavos inteiros."""
    if value_cents > limit_cents:
        return "ACIMA_LIMITE"
    if value_cents == limit_cents:
        return "NO_LIMITE"
    if value_cents / limit_cents >= T09_NEAR_LOWER:
        return "PROXIMO_LIMITE"
    return "ABAIXO_FAIXA"


def _eligible_national_purchases(staged: pd.DataFrame) -> pd.DataFrame:
    require_columns(
        staged,
        [
            "UG_ID",
            "FAVORECIDO_ID",
            "DATA_DT",
            "ANO_TRANSACAO",
            "VALOR_CENTAVOS",
            "EH_COMPRA_NACIONAL",
        ],
    )
    mask = (
        staged["EH_COMPRA_NACIONAL"].fillna(False)
        & staged["VALOR_CENTAVOS"].gt(0).fillna(False)
        & staged["DATA_DT"].notna()
        & staged["ANO_TRANSACAO"].notna()
    )
    base = staged.loc[mask].copy()
    if base.empty:
        return base
    base["ID_TRANSACAO"] = ensure_transaction_ids(staged).loc[base.index]
    base["DATA_DT"] = pd.to_datetime(base["DATA_DT"], errors="coerce")
    return base


def _scenario_status(values: pd.Series, limits: pd.Series) -> pd.Series:
    values_num = pd.to_numeric(values, errors="coerce")
    limits_num = pd.to_numeric(limits, errors="coerce")
    output = pd.Series("ABAIXO_FAIXA", index=values.index, dtype="string")
    output.loc[values_num.gt(limits_num)] = "ACIMA_LIMITE"
    output.loc[values_num.eq(limits_num)] = "NO_LIMITE"
    near = values_num.lt(limits_num) & values_num.div(limits_num).ge(T09_NEAR_LOWER)
    output.loc[near] = "PROXIMO_LIMITE"
    return output


def classify_transactions_against_limits(
    staged: pd.DataFrame, normative: pd.DataFrame | None = None
) -> pd.DataFrame:
    """Compara cada compra elegível com os dois cenários, sem escolher categoria real."""
    base = _eligible_national_purchases(staged)
    if base.empty:
        return pd.DataFrame()
    normative = build_normative_dimension() if normative is None else normative.copy()
    require_columns(
        normative,
        [
            "VIGENCIA_INICIO",
            "VIGENCIA_FIM",
            "CATEGORIA_CENARIO",
            "NORMA_REFERENCIA",
            "DISPOSITIVO_REFERENCIA",
            "LIMITE_CONCESSAO_CPGF",
            "LIMITE_CONCESSAO_CENTAVOS",
            "LIMITE_PEQUENO_VULTO_CPGF",
            "LIMITE_PEQUENO_VULTO_CENTAVOS",
        ],
    )

    output = base.copy()
    output["_NORM_MATCHES"] = 0
    category_fields = {
        "COMPRAS_SERVICOS": "COMPRAS",
        "OBRAS_ENGENHARIA": "ENGENHARIA",
    }
    for suffix in category_fields.values():
        for column in (
            f"LIMITE_PV_{suffix}",
            f"LIMITE_PV_{suffix}_CENTAVOS",
            f"LIMITE_CONCESSAO_{suffix}",
            f"LIMITE_CONCESSAO_{suffix}_CENTAVOS",
            f"NORMA_{suffix}",
            f"DISPOSITIVO_{suffix}",
        ):
            output[column] = pd.NA

    periods = normative[["VIGENCIA_INICIO", "VIGENCIA_FIM"]].drop_duplicates()
    for period in periods.itertuples(index=False):
        start = pd.Timestamp(period.VIGENCIA_INICIO)
        end = pd.Timestamp(period.VIGENCIA_FIM)
        period_rows = normative.loc[
            normative["VIGENCIA_INICIO"].eq(start) & normative["VIGENCIA_FIM"].eq(end)
        ]
        if set(period_rows["CATEGORIA_CENARIO"]) != set(category_fields):
            raise AssertionError("T09: cada vigência deve possuir exatamente os dois cenários.")
        mask = output["DATA_DT"].between(start, end)
        output.loc[mask, "_NORM_MATCHES"] += 1
        for category, suffix in category_fields.items():
            row = period_rows.loc[period_rows["CATEGORIA_CENARIO"].eq(category)].iloc[0]
            output.loc[mask, f"LIMITE_PV_{suffix}"] = row["LIMITE_PEQUENO_VULTO_CPGF"]
            output.loc[mask, f"LIMITE_PV_{suffix}_CENTAVOS"] = row[
                "LIMITE_PEQUENO_VULTO_CENTAVOS"
            ]
            output.loc[mask, f"LIMITE_CONCESSAO_{suffix}"] = row[
                "LIMITE_CONCESSAO_CPGF"
            ]
            output.loc[mask, f"LIMITE_CONCESSAO_{suffix}_CENTAVOS"] = row[
                "LIMITE_CONCESSAO_CENTAVOS"
            ]
            output.loc[mask, f"NORMA_{suffix}"] = row["NORMA_REFERENCIA"]
            output.loc[mask, f"DISPOSITIVO_{suffix}"] = row["DISPOSITIVO_REFERENCIA"]

    if not output["_NORM_MATCHES"].eq(1).all():
        missing = int(output["_NORM_MATCHES"].ne(1).sum())
        raise AssertionError(
            f"T09: {missing} transações não possuem uma única vigência normativa aplicável."
        )
    output = output.drop(columns="_NORM_MATCHES")

    for suffix in category_fields.values():
        output[f"LIMITE_PV_{suffix}_CENTAVOS"] = pd.to_numeric(
            output[f"LIMITE_PV_{suffix}_CENTAVOS"]
        ).astype("int64")
        output[f"LIMITE_CONCESSAO_{suffix}_CENTAVOS"] = pd.to_numeric(
            output[f"LIMITE_CONCESSAO_{suffix}_CENTAVOS"]
        ).astype("int64")

    output["STATUS_COMPRAS"] = _scenario_status(
        output["VALOR_CENTAVOS"], output["LIMITE_PV_COMPRAS_CENTAVOS"]
    )
    output["STATUS_ENGENHARIA"] = _scenario_status(
        output["VALOR_CENTAVOS"], output["LIMITE_PV_ENGENHARIA_CENTAVOS"]
    )
    output["RATIO_PV_COMPRAS"] = (
        output["VALOR_CENTAVOS"] / output["LIMITE_PV_COMPRAS_CENTAVOS"]
    )
    output["RATIO_PV_ENGENHARIA"] = (
        output["VALOR_CENTAVOS"] / output["LIMITE_PV_ENGENHARIA_CENTAVOS"]
    )
    output["MODO_APLICABILIDADE"] = T09_MODE
    output["APLICABILIDADE_JURIDICA"] = T09_LEGAL_APPLICABILITY

    compras = output["STATUS_COMPRAS"]
    engenharia = output["STATUS_ENGENHARIA"]
    both_above = compras.eq("ACIMA_LIMITE") & engenharia.eq("ACIMA_LIMITE")
    any_above = compras.eq("ACIMA_LIMITE") | engenharia.eq("ACIMA_LIMITE")
    any_exact = compras.eq("NO_LIMITE") | engenharia.eq("NO_LIMITE")
    any_near = compras.eq("PROXIMO_LIMITE") | engenharia.eq("PROXIMO_LIMITE")

    output["STATUS_T09"] = "ABAIXO_FAIXAS"
    output.loc[any_near, "STATUS_T09"] = "PROXIMO_LIMITE"
    output.loc[any_exact, "STATUS_T09"] = "NO_LIMITE_PELO_MENOS_UM_CENARIO"
    output.loc[any_above, "STATUS_T09"] = "ACIMA_PELO_MENOS_UM_CENARIO"
    output.loc[both_above, "STATUS_T09"] = "ACIMA_AMBOS_CENARIOS"

    output["NIVEL_TRIAGEM"] = "SEM_SINAL"
    output.loc[any_near | any_exact, "NIVEL_TRIAGEM"] = "INFORMATIVO"
    output.loc[any_above, "NIVEL_TRIAGEM"] = "ATENCAO"
    output.loc[both_above, "NIVEL_TRIAGEM"] = "REFORCADO"
    return output.reset_index(drop=True)


def build_limit_scenarios(classified: pd.DataFrame) -> pd.DataFrame:
    """Materializa os dois cenários por transação quando o consumidor precisar."""
    if classified.empty:
        return pd.DataFrame()
    pieces = []
    for category, suffix in (
        ("COMPRAS_SERVICOS", "COMPRAS"),
        ("OBRAS_ENGENHARIA", "ENGENHARIA"),
    ):
        piece = classified[
            [
                "ID_TRANSACAO",
                "UG_ID",
                "FAVORECIDO_ID",
                "DATA_DT",
                "ANO_TRANSACAO",
                "VALOR_CENTAVOS",
                f"NORMA_{suffix}",
                f"DISPOSITIVO_{suffix}",
                f"LIMITE_CONCESSAO_{suffix}",
                f"LIMITE_CONCESSAO_{suffix}_CENTAVOS",
                f"LIMITE_PV_{suffix}",
                f"LIMITE_PV_{suffix}_CENTAVOS",
                f"STATUS_{suffix}",
                f"RATIO_PV_{suffix}",
            ]
        ].copy()
        piece["CATEGORIA_CENARIO"] = category
        piece = piece.rename(
            columns={
                f"NORMA_{suffix}": "NORMA_REFERENCIA",
                f"DISPOSITIVO_{suffix}": "DISPOSITIVO_REFERENCIA",
                f"LIMITE_CONCESSAO_{suffix}": "LIMITE_CONCESSAO_CPGF",
                f"LIMITE_CONCESSAO_{suffix}_CENTAVOS": "LIMITE_CONCESSAO_CENTAVOS",
                f"LIMITE_PV_{suffix}": "LIMITE_PEQUENO_VULTO_CPGF",
                f"LIMITE_PV_{suffix}_CENTAVOS": "LIMITE_PEQUENO_VULTO_CENTAVOS",
                f"STATUS_{suffix}": "STATUS_CENARIO",
                f"RATIO_PV_{suffix}": "RATIO_PEQUENO_VULTO",
            }
        )
        pieces.append(piece)
    scenarios = pd.concat(pieces, ignore_index=True)
    if len(scenarios) != 2 * len(classified):
        raise AssertionError("T09: cobertura esperada de dois cenários por transação não foi atendida.")
    return scenarios


def detect_limit_context_signals(staged: pd.DataFrame) -> pd.DataFrame:
    """Retém transações próximas, iguais ou acima em ao menos um cenário."""
    classified = classify_transactions_against_limits(staged)
    if classified.empty:
        return classified
    signals = classified.loc[classified["STATUS_T09"].ne("ABAIXO_FAIXAS")].copy()
    if signals.empty:
        signals.insert(0, "ID_SINAL", pd.Series(dtype="string"))
        return signals
    signals.insert(
        0,
        "ID_SINAL",
        signals.apply(
            lambda row: keyed_signal_id_md5(
                "T09",
                row["ID_TRANSACAO"],
                row["STATUS_COMPRAS"],
                row["STATUS_ENGENHARIA"],
            ),
            axis=1,
        ),
    )
    return signals.reset_index(drop=True)


def aggregate_limit_context(classified: pd.DataFrame) -> pd.DataFrame:
    """Agrega T09 de forma descritiva por UG × fornecedor × ano."""
    if classified.empty:
        return pd.DataFrame()
    base = classified.loc[classified["FAVORECIDO_ID"].notna()].copy()
    if base.empty:
        return pd.DataFrame()
    base["EH_T09"] = base["STATUS_T09"].ne("ABAIXO_FAIXAS")
    base["VALOR_T09_CENTAVOS"] = base["VALOR_CENTAVOS"].where(base["EH_T09"], 0)
    for status, suffix in (
        ("PROXIMO_LIMITE", "PROXIMO"),
        ("NO_LIMITE", "NO_LIMITE"),
        ("ACIMA_LIMITE", "ACIMA"),
    ):
        base[f"COMPRAS_{suffix}"] = base["STATUS_COMPRAS"].eq(status)
        base[f"ENGENHARIA_{suffix}"] = base["STATUS_ENGENHARIA"].eq(status)

    keys = ["UG_ID", "FAVORECIDO_ID", "ANO_TRANSACAO"]
    grouped = (
        base.groupby(keys, as_index=False, sort=False)
        .agg(
            N_COMPRAS=("VALOR_CENTAVOS", "size"),
            VALOR_TOTAL_CENTAVOS=("VALOR_CENTAVOS", "sum"),
            N_TRANSACOES_T09=("EH_T09", "sum"),
            VALOR_TRANSACOES_T09_CENTAVOS=("VALOR_T09_CENTAVOS", "sum"),
            N_COMPRAS_PROXIMO=("COMPRAS_PROXIMO", "sum"),
            N_COMPRAS_NO_LIMITE=("COMPRAS_NO_LIMITE", "sum"),
            N_COMPRAS_ACIMA=("COMPRAS_ACIMA", "sum"),
            N_ENGENHARIA_PROXIMO=("ENGENHARIA_PROXIMO", "sum"),
            N_ENGENHARIA_NO_LIMITE=("ENGENHARIA_NO_LIMITE", "sum"),
            N_ENGENHARIA_ACIMA=("ENGENHARIA_ACIMA", "sum"),
            MAX_RATIO_PV_COMPRAS=("RATIO_PV_COMPRAS", "max"),
            MAX_RATIO_PV_ENGENHARIA=("RATIO_PV_ENGENHARIA", "max"),
        )
    )
    grouped["SHARE_TRANSACOES_T09"] = grouped["N_TRANSACOES_T09"] / grouped[
        "N_COMPRAS"
    ]
    grouped["APLICABILIDADE_AGREGADO"] = "DESCRITIVO_NAO_CONCLUSIVO"
    return grouped


def run_t09(
    staged: pd.DataFrame, *, include_scenarios: bool = False
) -> dict[str, pd.DataFrame]:
    """Executa T09; cenários 2× são materializados apenas sob demanda."""
    normative = build_normative_dimension()
    classified = classify_transactions_against_limits(staged, normative)
    signals = classified.loc[classified["STATUS_T09"].ne("ABAIXO_FAIXAS")].copy()
    if not signals.empty:
        signals.insert(
            0,
            "ID_SINAL",
            signals.apply(
                lambda row: keyed_signal_id_md5(
                    "T09",
                    row["ID_TRANSACAO"],
                    row["STATUS_COMPRAS"],
                    row["STATUS_ENGENHARIA"],
                ),
                axis=1,
            ),
        )
    else:
        signals.insert(0, "ID_SINAL", pd.Series(dtype="string"))
    return {
        "normative_dimension": normative,
        "classified": classified,
        "signals": signals.reset_index(drop=True),
        "aggregates": aggregate_limit_context(classified),
        "scenarios": build_limit_scenarios(classified) if include_scenarios else pd.DataFrame(),
    }
