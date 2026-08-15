from __future__ import annotations

import math
from itertools import combinations

import numpy as np
import pandas as pd

from .eligibility import MIN_NEGATIVES_STATISTICAL, MIN_POSITIVES_STATISTICAL


def pairwise_binary_metrics(
    frame: pd.DataFrame,
    flags: list[str] | tuple[str, ...],
    unit: str,
    *,
    year: int | None = None,
    supplier_exposure_band: str | None = None,
    annual_exposure_decile: int | None = None,
    min_positives: int = MIN_POSITIVES_STATISTICAL,
    min_negatives: int = MIN_NEGATIVES_STATISTICAL,
) -> pd.DataFrame:
    """Calcula Jaccard, Phi e condicionais para todos os pares de flags binárias."""
    missing = [flag for flag in flags if flag not in frame.columns]
    if missing:
        raise ValueError(f"Flags ausentes para sobreposição: {missing}")

    rows: list[dict[str, object]] = []
    n = len(frame)
    for a, b in combinations(flags, 2):
        xa = frame[a].fillna(0).astype(int)
        xb = frame[b].fillna(0).astype(int)
        if (~xa.isin([0, 1])).any() or (~xb.isin([0, 1])).any():
            raise ValueError(f"Flags {a}/{b} devem conter apenas 0/1.")

        a_arr = xa.to_numpy()
        b_arr = xb.to_numpy()
        n11 = int(((a_arr == 1) & (b_arr == 1)).sum())
        n10 = int(((a_arr == 1) & (b_arr == 0)).sum())
        n01 = int(((a_arr == 0) & (b_arr == 1)).sum())
        n00 = n - n11 - n10 - n01
        union = n11 + n10 + n01

        jaccard = n11 / union if union else np.nan
        denom_phi = math.sqrt(
            (n11 + n10) * (n01 + n00) * (n11 + n01) * (n10 + n00)
        )
        phi = ((n11 * n00 - n10 * n01) / denom_phi) if denom_phi else np.nan

        n_a = n11 + n10
        n_b = n11 + n01
        eligible_a = n_a >= min_positives and (n - n_a) >= min_negatives
        eligible_b = n_b >= min_positives and (n - n_b) >= min_negatives

        rows.append(
            {
                "UNIDADE_ANALISE": unit,
                "ANO": year,
                "BANDA_EXPOSICAO_FORNECEDOR": supplier_exposure_band,
                "DECIL_EXPOSICAO_ANUAL": annual_exposure_decile,
                "REGRA_A": a,
                "REGRA_B": b,
                "N_UNIVERSO": n,
                "N_A": n_a,
                "N_B": n_b,
                "ELEGIVEL_A_NO_RECORTE": eligible_a,
                "ELEGIVEL_B_NO_RECORTE": eligible_b,
                "DIAGNOSTICO_PAR_NO_RECORTE": (
                    "SUFICIENTE"
                    if eligible_a and eligible_b
                    else "CAUTELA_RARIDADE_NO_RECORTE"
                ),
                "INTERSECAO": n11,
                "A_APENAS": n10,
                "B_APENAS": n01,
                "NENHUMA": n00,
                "UNIAO": union,
                "JACCARD": jaccard,
                "PHI": phi,
                "P_B_DADO_A": n11 / n_a if n_a else np.nan,
                "P_A_DADO_B": n11 / n_b if n_b else np.nan,
            }
        )

    return pd.DataFrame(rows)


def add_global_pair_eligibility(
    pairs: pd.DataFrame,
    eligibility: pd.DataFrame,
) -> pd.DataFrame:
    """Anexa a suficiência global de cada flag sem apagar métricas de recortes raros."""
    required = {"REGRA", "ELEGIBILIDADE_DIAGNOSTICO_ESTATISTICO"}
    if not required.issubset(eligibility.columns):
        raise ValueError("Tabela de elegibilidade global incompleta.")
    if pairs.empty:
        return pairs.copy()

    mapping = eligibility.set_index("REGRA")[
        "ELEGIBILIDADE_DIAGNOSTICO_ESTATISTICO"
    ].to_dict()
    result = pairs.copy()
    result["ELEGIBILIDADE_A_GLOBAL"] = result["REGRA_A"].map(mapping)
    result["ELEGIBILIDADE_B_GLOBAL"] = result["REGRA_B"].map(mapping)
    result["DIAGNOSTICO_PAR_GLOBAL"] = np.where(
        result["ELEGIBILIDADE_A_GLOBAL"].eq("SUFICIENTE")
        & result["ELEGIBILIDADE_B_GLOBAL"].eq("SUFICIENTE"),
        "SUFICIENTE",
        "CAUTELA_RARIDADE",
    )
    return result


def square_metric_matrix(
    pairs: pd.DataFrame,
    flags: list[str] | tuple[str, ...],
    metric: str,
) -> pd.DataFrame:
    """Converte a tabela de pares em matriz simétrica para visualização/serving."""
    if metric not in pairs.columns and not pairs.empty:
        raise ValueError(f"Métrica ausente: {metric}")
    result = pd.DataFrame(
        np.eye(len(flags)),
        index=list(flags),
        columns=list(flags),
    )
    for row in pairs.itertuples(index=False):
        a = row.REGRA_A
        b = row.REGRA_B
        value = getattr(row, metric)
        result.loc[a, b] = value
        result.loc[b, a] = value
    return result.reset_index().rename(columns={"index": "REGRA"})


def pairwise_by_year(
    frame: pd.DataFrame,
    flags: list[str] | tuple[str, ...],
    unit: str,
    *,
    year_column: str = "ANO",
) -> pd.DataFrame:
    if year_column not in frame.columns:
        raise ValueError(f"Coluna de ano ausente: {year_column}")
    pieces = [
        pairwise_binary_metrics(group, flags, unit, year=int(year))
        for year, group in frame.groupby(year_column, dropna=True)
        if len(group)
    ]
    return pd.concat(pieces, ignore_index=True) if pieces else pd.DataFrame()


def pairwise_by_supplier_exposure(
    frame: pd.DataFrame,
    flags: list[str] | tuple[str, ...],
    unit: str = "UG_FORNECEDOR_ANO",
    *,
    band_column: str = "BANDA_EXPOSICAO_FORNECEDOR",
) -> pd.DataFrame:
    if band_column not in frame.columns:
        raise ValueError(f"Coluna de banda ausente: {band_column}")
    pieces = [
        pairwise_binary_metrics(
            group,
            flags,
            unit,
            supplier_exposure_band=str(band),
        )
        for band, group in frame.groupby(band_column, dropna=True)
        if len(group)
    ]
    return pd.concat(pieces, ignore_index=True) if pieces else pd.DataFrame()


def pairwise_by_annual_decile(
    frame: pd.DataFrame,
    flags: list[str] | tuple[str, ...],
    unit: str = "UG_ANO",
    *,
    decile_column: str = "DECIL_EXPOSICAO_ANUAL",
) -> pd.DataFrame:
    if decile_column not in frame.columns:
        raise ValueError(f"Coluna de decil ausente: {decile_column}")
    pieces = [
        pairwise_binary_metrics(
            group,
            flags,
            unit,
            annual_exposure_decile=int(decile),
        )
        for decile, group in frame.groupby(decile_column, dropna=True)
        if len(group)
    ]
    return pd.concat(pieces, ignore_index=True) if pieces else pd.DataFrame()
