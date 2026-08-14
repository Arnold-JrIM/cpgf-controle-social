from __future__ import annotations

import numpy as np
import pandas as pd

from .base import keyed_signal_id_sha256, require_columns

T08_MIN_N_APPLY = 300
T08_MIN_N_FORMAL = 1000
T08_MIN_N_ROBUST = 3000
T08_MIN_D12_CENTS = 1_000
T08_MIN_COMPARABLE_UGS = 10
T08_COMPLETE_YEAR_START = 2013
T08_COMPLETE_YEAR_END = 2025
T08_PERSISTENCE_MIN_YEARS = 3
T08_PERSISTENCE_MIN_RATIO = 0.50

MAD_LIMITS_D1 = (
    (0.006, "Conformidade próxima"),
    (0.012, "Conformidade aceitável"),
    (0.015, "Conformidade marginalmente aceitável"),
)
MAD_LIMITS_D12 = (
    (0.0012, "Conformidade próxima"),
    (0.0018, "Conformidade aceitável"),
    (0.0022, "Conformidade marginalmente aceitável"),
)


def benford_probabilities(kind: str) -> pd.DataFrame:
    """Retorna a distribuição teórica de Benford para D1 ou D12."""
    if kind == "D1":
        digits = np.arange(1, 10)
    elif kind == "D12":
        digits = np.arange(10, 100)
    else:
        raise ValueError("kind deve ser 'D1' ou 'D12'.")
    return pd.DataFrame(
        {
            "DIGITO": digits,
            "PROB_ESPERADA": np.log10(1 + 1 / digits),
        }
    )


def classify_mad(mad: float, kind: str) -> str:
    """Classifica o MAD pelos limiares usados na especificação congelada."""
    limits = MAD_LIMITS_D1 if kind == "D1" else MAD_LIMITS_D12
    for limit, label in limits:
        if mad <= limit:
            return label
    return "Não conformidade"


def sample_status(n: int) -> str:
    """Classifica a suficiência numérica sem produzir conclusão substantiva."""
    if n < T08_MIN_N_APPLY:
        return "NAO_APLICAR"
    if n < T08_MIN_N_FORMAL:
        return "EXPLORATORIO"
    if n >= T08_MIN_N_ROBUST:
        return "FORMAL_ROBUSTEZ_MAIOR"
    return "FORMAL"


def _eligible_national_purchases(staged: pd.DataFrame) -> pd.DataFrame:
    require_columns(
        staged,
        ["UG_ID", "ANO_TRANSACAO", "VALOR_CENTAVOS", "EH_COMPRA_NACIONAL"],
    )
    mask = (
        staged["EH_COMPRA_NACIONAL"].fillna(False)
        & staged["VALOR_CENTAVOS"].gt(0).fillna(False)
        & staged["UG_ID"].notna()
        & staged["ANO_TRANSACAO"].notna()
    )
    base = staged.loc[mask].copy()
    if base.empty:
        return base

    values = base["VALOR_CENTAVOS"].astype("float64").to_numpy()
    mantissa = values / np.power(10.0, np.floor(np.log10(values)))
    base["D1"] = np.clip(np.floor(mantissa + 1e-10), 1, 9).astype("int16")
    base["D12"] = np.clip(np.floor(mantissa * 10 + 1e-10), 10, 99).astype("int16")
    return base


def _summarize_group(values: pd.Series, kind: str) -> tuple[int, float, str, float]:
    n = int(values.size)
    probs = benford_probabilities(kind)
    counts = values.value_counts().rename_axis("DIGITO").rename("AC").reset_index()
    table = probs.merge(counts, on="DIGITO", how="left")
    table["AC"] = table["AC"].fillna(0).astype("float64")
    table["AP"] = table["AC"] / n
    table["EC"] = table["PROB_ESPERADA"] * n
    diff = table["AP"] - table["PROB_ESPERADA"]
    mad = float(diff.abs().mean())
    chi2 = float((((table["AC"] - table["EC"]) ** 2) / table["EC"]).sum())
    return n, mad, classify_mad(mad, kind), chi2


def compute_benford_ug_year(staged: pd.DataFrame) -> pd.DataFrame:
    """Calcula D1 e D12 por UG × exercício conforme T08 1.2.0.

    D1 considera todas as compras nacionais positivas. D12 principal considera
    apenas valores a partir de R$ 10. Abaixo de 300 observações o teste não é
    aplicado; os indicadores de tamanho permanecem disponíveis.
    """
    base = _eligible_national_purchases(staged)
    if base.empty:
        return pd.DataFrame()

    keys = ["UG_ID", "ANO_TRANSACAO"]
    eligibility = (
        base.groupby(keys, sort=False, dropna=False)
        .agg(
            N_D1=("VALOR_CENTAVOS", "size"),
            VALORES_UNICOS=("VALOR_CENTAVOS", "nunique"),
            MINIMO_CENTAVOS=("VALOR_CENTAVOS", "min"),
            MEDIANA_CENTAVOS=("VALOR_CENTAVOS", "median"),
            MEDIA_CENTAVOS=("VALOR_CENTAVOS", "mean"),
            MAXIMO_CENTAVOS=("VALOR_CENTAVOS", "max"),
        )
        .reset_index()
    )
    d12_n = (
        base.loc[base["VALOR_CENTAVOS"].ge(T08_MIN_D12_CENTS)]
        .groupby(keys, sort=False)
        .size()
        .rename("N_D12")
        .reset_index()
    )
    eligibility = eligibility.merge(d12_n, on=keys, how="left", validate="one_to_one")
    eligibility["N_D12"] = eligibility["N_D12"].fillna(0).astype("int64")
    eligibility["STATUS_D1"] = eligibility["N_D1"].map(sample_status)
    eligibility["STATUS_D12"] = eligibility["N_D12"].map(sample_status)

    d1_rows: list[dict[str, object]] = []
    for (ug, year), group in base.groupby(keys, sort=False):
        if len(group) < T08_MIN_N_APPLY:
            continue
        n, mad, classification, chi2 = _summarize_group(group["D1"], "D1")
        d1_rows.append(
            {
                "UG_ID": ug,
                "ANO_TRANSACAO": year,
                "N_D1_CALC": n,
                "MAD_D1": mad,
                "CLASSIFICACAO_D1": classification,
                "CHI2_D1": chi2,
            }
        )

    d12_base = base.loc[base["VALOR_CENTAVOS"].ge(T08_MIN_D12_CENTS)]
    d12_rows: list[dict[str, object]] = []
    for (ug, year), group in d12_base.groupby(keys, sort=False):
        if len(group) < T08_MIN_N_APPLY:
            continue
        n, mad, classification, chi2 = _summarize_group(group["D12"], "D12")
        d12_rows.append(
            {
                "UG_ID": ug,
                "ANO_TRANSACAO": year,
                "N_D12_CALC": n,
                "MAD_D12": mad,
                "CLASSIFICACAO_D12": classification,
                "CHI2_D12": chi2,
            }
        )

    indicators = eligibility
    if d1_rows:
        indicators = indicators.merge(pd.DataFrame(d1_rows), on=keys, how="left")
    else:
        for column in ("N_D1_CALC", "MAD_D1", "CLASSIFICACAO_D1", "CHI2_D1"):
            indicators[column] = pd.NA
    if d12_rows:
        indicators = indicators.merge(pd.DataFrame(d12_rows), on=keys, how="left")
    else:
        for column in ("N_D12_CALC", "MAD_D12", "CLASSIFICACAO_D12", "CHI2_D12"):
            indicators[column] = pd.NA
    return indicators.reset_index(drop=True)


def rank_relative_benford(indicators: pd.DataFrame) -> pd.DataFrame:
    """Prioriza relativamente UG-anos formais, preservando empates no P90."""
    require_columns(indicators, ["UG_ID", "ANO_TRANSACAO", "N_D12", "MAD_D12"])
    formal = indicators.loc[
        indicators["N_D12"].ge(T08_MIN_N_FORMAL).fillna(False)
        & indicators["ANO_TRANSACAO"]
        .between(T08_COMPLETE_YEAR_START, T08_COMPLETE_YEAR_END)
        .fillna(False)
        & indicators["MAD_D12"].notna()
    ].copy()
    if formal.empty:
        return formal

    formal["N_UG_COMPARAVEIS_ANO"] = formal.groupby("ANO_TRANSACAO")[
        "UG_ID"
    ].transform("count")
    formal["PERCENT_RANK_MAD_D12"] = formal.groupby("ANO_TRANSACAO")[
        "MAD_D12"
    ].rank(pct=True, method="average")
    formal["LIMIAR_P90_MAD_D12"] = formal.groupby("ANO_TRANSACAO")[
        "MAD_D12"
    ].transform(lambda values: values.quantile(0.90))
    formal["ANO_RANK_VALIDO"] = formal["N_UG_COMPARAVEIS_ANO"].ge(
        T08_MIN_COMPARABLE_UGS
    )
    formal["TOP_DECIL_MAD_D12"] = formal["ANO_RANK_VALIDO"] & formal[
        "MAD_D12"
    ].ge(formal["LIMIAR_P90_MAD_D12"])
    formal["NAO_CONFORME_D12_ABSOLUTO"] = formal["MAD_D12"].gt(0.0022)
    return formal.reset_index(drop=True)


def build_benford_signals(ranked: pd.DataFrame) -> pd.DataFrame:
    """Transforma extremos relativos válidos em sinais contextuais T08."""
    if ranked.empty:
        return ranked.copy()
    require_columns(
        ranked,
        ["UG_ID", "ANO_TRANSACAO", "MAD_D12", "TOP_DECIL_MAD_D12"],
    )
    signals = ranked.loc[ranked["TOP_DECIL_MAD_D12"].fillna(False)].copy()
    if signals.empty:
        signals.insert(0, "ID_SINAL", pd.Series(dtype="string"))
        signals["NIVEL_TRIAGEM"] = pd.Series(dtype="string")
        return signals

    signals.insert(
        0,
        "ID_SINAL",
        signals.apply(
            lambda row: keyed_signal_id_sha256(
                "T08",
                row["UG_ID"],
                int(row["ANO_TRANSACAO"]),
                round(float(row["MAD_D12"]), 8),
            ),
            axis=1,
        ),
    )
    signals["NIVEL_TRIAGEM"] = "ATENCAO"
    return signals.reset_index(drop=True)


def compute_benford_persistence(ranked: pd.DataFrame) -> pd.DataFrame:
    """Resume persistência relativa como diagnóstico auxiliar por UG."""
    if ranked.empty:
        return pd.DataFrame()
    valid = ranked.loc[ranked["ANO_RANK_VALIDO"].fillna(False)].copy()
    if valid.empty:
        return pd.DataFrame()
    persistence = (
        valid.groupby("UG_ID", as_index=False)
        .agg(
            ANOS_COMPARAVEIS=("ANO_TRANSACAO", "nunique"),
            ANOS_TOP_DECIL=("TOP_DECIL_MAD_D12", "sum"),
            PRIMEIRO_ANO=("ANO_TRANSACAO", "min"),
            ULTIMO_ANO=("ANO_TRANSACAO", "max"),
            MAD_D12_MEDIO=("MAD_D12", "mean"),
            MAD_D12_MAX=("MAD_D12", "max"),
        )
    )
    persistence["RATIO_TOP_DECIL"] = (
        persistence["ANOS_TOP_DECIL"] / persistence["ANOS_COMPARAVEIS"]
    )
    persistence["PERSISTENCIA_RELATIVA_ELEVADA"] = persistence[
        "ANOS_COMPARAVEIS"
    ].ge(T08_PERSISTENCE_MIN_YEARS) & persistence["RATIO_TOP_DECIL"].ge(
        T08_PERSISTENCE_MIN_RATIO
    )
    return persistence.sort_values(
        ["PERSISTENCIA_RELATIVA_ELEVADA", "RATIO_TOP_DECIL", "ANOS_TOP_DECIL"],
        ascending=[False, False, False],
    ).reset_index(drop=True)


def compute_summation_d12(staged: pd.DataFrame) -> pd.DataFrame:
    """Executa o Summation Test global D12 sem criar limiar arbitrário."""
    base = _eligible_national_purchases(staged)
    base = base.loc[base["VALOR_CENTAVOS"].ge(T08_MIN_D12_CENTS)]
    probs = pd.DataFrame({"DIGITO": np.arange(10, 100)})
    if base.empty:
        probs["FREQUENCIA"] = 0
        probs["SOMA_CENTAVOS"] = 0
        probs["SHARE_SOMA"] = 0.0
        probs["ESPERADO"] = 1 / 90
        probs["DESVIO_SOMA"] = -(1 / 90)
        return probs

    grouped = (
        base.groupby("D12", as_index=False)
        .agg(FREQUENCIA=("VALOR_CENTAVOS", "size"), SOMA_CENTAVOS=("VALOR_CENTAVOS", "sum"))
        .rename(columns={"D12": "DIGITO"})
    )
    output = probs.merge(grouped, on="DIGITO", how="left").fillna(
        {"FREQUENCIA": 0, "SOMA_CENTAVOS": 0}
    )
    total = float(output["SOMA_CENTAVOS"].sum())
    output["SHARE_SOMA"] = output["SOMA_CENTAVOS"] / total if total else 0.0
    output["ESPERADO"] = 1 / 90
    output["DESVIO_SOMA"] = output["SHARE_SOMA"] - output["ESPERADO"]
    return output


def run_t08(staged: pd.DataFrame) -> dict[str, pd.DataFrame]:
    indicators = compute_benford_ug_year(staged)
    ranked = rank_relative_benford(indicators) if not indicators.empty else pd.DataFrame()
    signals = build_benford_signals(ranked)
    return {
        "indicators": indicators,
        "ranked": ranked,
        "signals": signals,
        "persistence": compute_benford_persistence(ranked),
        "summation": compute_summation_d12(staged),
    }
