from __future__ import annotations

import numpy as np
import pandas as pd

MIN_POSITIVES_STATISTICAL = 30
MIN_NEGATIVES_STATISTICAL = 30


def evaluate_flag_eligibility(
    frame: pd.DataFrame,
    flags: list[str] | tuple[str, ...],
    unit: str,
    *,
    min_positives: int = MIN_POSITIVES_STATISTICAL,
    min_negatives: int = MIN_NEGATIVES_STATISTICAL,
) -> pd.DataFrame:
    """Avalia suficiência estatística sem remover flags raras do motor."""
    missing = [flag for flag in flags if flag not in frame.columns]
    if missing:
        raise ValueError(f"Flags ausentes para elegibilidade: {missing}")
    if min_positives < 1 or min_negatives < 1:
        raise ValueError("Os mínimos estatísticos devem ser positivos.")

    rows: list[dict[str, object]] = []
    for flag in flags:
        series = frame[flag].fillna(0).astype(int)
        invalid = ~series.isin([0, 1])
        if invalid.any():
            raise ValueError(f"{flag} contém valores fora de 0/1.")

        n = len(series)
        n_pos = int(series.eq(1).sum())
        n_neg = int(series.eq(0).sum())
        if n_pos == 0 or n_neg == 0:
            status = "SEM_VARIACAO"
        elif n_pos < min_positives or n_neg < min_negatives:
            status = "DIAGNOSTICO_ESTATISTICO_INSUFICIENTE"
        else:
            status = "SUFICIENTE"

        rows.append(
            {
                "UNIDADE_ANALISE": unit,
                "REGRA": flag,
                "N_UNIVERSO": n,
                "N_POSITIVOS": n_pos,
                "N_NEGATIVOS": n_neg,
                "PREVALENCIA": n_pos / n if n else np.nan,
                "MIN_POSITIVOS_EXIGIDO": min_positives,
                "MIN_NEGATIVOS_EXIGIDO": min_negatives,
                "ELEGIBILIDADE_DIAGNOSTICO_ESTATISTICO": status,
                "ELEGIVEL_PCA_VIF": status == "SUFICIENTE",
            }
        )

    return pd.DataFrame(rows)
