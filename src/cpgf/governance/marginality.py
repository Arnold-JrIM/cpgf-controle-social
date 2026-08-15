from __future__ import annotations

import numpy as np
import pandas as pd


def marginal_contribution(
    frame: pd.DataFrame,
    flags: list[str] | tuple[str, ...],
    unit: str,
    *,
    kind: str = "TRILHA",
) -> pd.DataFrame:
    """Mede quantas unidades deixariam a união caso cada flag fosse retirada."""
    missing = [flag for flag in flags if flag not in frame.columns]
    if missing:
        raise ValueError(f"Flags ausentes para contribuição marginal: {missing}")

    values = frame[list(flags)].fillna(0).astype(int)
    invalid = ~values.isin([0, 1])
    if invalid.any().any():
        raise ValueError("As flags de contribuição marginal devem ser binárias 0/1.")

    summed = values.sum(axis=1)
    union_total = int(summed.gt(0).sum())
    rows: list[dict[str, object]] = []

    for flag in flags:
        active = values[flag].eq(1)
        other_columns = [column for column in flags if column != flag]
        others = values[other_columns].sum(axis=1) if other_columns else pd.Series(0, index=values.index)
        exclusive = active & others.eq(0)

        n_flag = int(active.sum())
        n_exclusive = int(exclusive.sum())
        union_without = int(others.gt(0).sum())

        rows.append(
            {
                "UNIDADE_ANALISE": unit,
                "TIPO": kind,
                "REGRA_OU_FAMILIA": flag,
                "N_UNIVERSO": len(frame),
                "N_UNIAO_MOTOR": union_total,
                "N_SINALIZADOS": n_flag,
                "N_EXCLUSIVOS": n_exclusive,
                "CONTRIBUICAO_MARGINAL_PCT": n_exclusive / n_flag if n_flag else np.nan,
                "N_UNIAO_SEM_REGRA": union_without,
                "PERDA_UNIDADES_SE_REMOVER": union_total - union_without,
                "ZERO_EXCLUSIVOS": n_exclusive == 0,
            }
        )

    return pd.DataFrame(rows)


def marginal_by_supplier_exposure(
    frame: pd.DataFrame,
    flags: list[str] | tuple[str, ...],
    *,
    band_column: str = "BANDA_EXPOSICAO_FORNECEDOR",
) -> pd.DataFrame:
    if band_column not in frame.columns:
        raise ValueError(f"Coluna de banda ausente: {band_column}")
    pieces: list[pd.DataFrame] = []
    for band, group in frame.groupby(band_column, dropna=True):
        if not len(group):
            continue
        piece = marginal_contribution(group, flags, "UG_FORNECEDOR_ANO")
        piece["BANDA_EXPOSICAO_FORNECEDOR"] = str(band)
        pieces.append(piece)
    return pd.concat(pieces, ignore_index=True) if pieces else pd.DataFrame()


def marginal_by_annual_decile(
    frame: pd.DataFrame,
    flags: list[str] | tuple[str, ...],
    *,
    decile_column: str = "DECIL_EXPOSICAO_ANUAL",
) -> pd.DataFrame:
    if decile_column not in frame.columns:
        raise ValueError(f"Coluna de decil ausente: {decile_column}")
    pieces: list[pd.DataFrame] = []
    for decile, group in frame.groupby(decile_column, dropna=True):
        if not len(group):
            continue
        piece = marginal_contribution(group, flags, "UG_ANO")
        piece["DECIL_EXPOSICAO_ANUAL"] = int(decile)
        pieces.append(piece)
    return pd.concat(pieces, ignore_index=True) if pieces else pd.DataFrame()
