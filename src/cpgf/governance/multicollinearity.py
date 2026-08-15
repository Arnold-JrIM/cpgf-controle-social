from __future__ import annotations

import numpy as np
import pandas as pd

from .eligibility import (
    MIN_NEGATIVES_STATISTICAL,
    MIN_POSITIVES_STATISTICAL,
    evaluate_flag_eligibility,
)

VIF_COLUMNS: tuple[str, ...] = (
    "UNIDADE_ANALISE",
    "TIPO",
    "REGRA_OU_FAMILIA",
    "N_UNIVERSO",
    "N_POSITIVOS",
    "N_NEGATIVOS",
    "PREVALENCIA",
    "ELEGIBILIDADE_DIAGNOSTICO_ESTATISTICO",
    "N_VARIAVEIS_ELEGIVEIS_MODELO",
    "R2_AUXILIAR",
    "TOLERANCIA",
    "VIF",
    "STATUS_VIF",
)

CONDITION_COLUMNS: tuple[str, ...] = (
    "UNIDADE_ANALISE",
    "TIPO",
    "COMPONENTE",
    "N_UNIVERSO",
    "N_VARIAVEIS_ELEGIVEIS_MODELO",
    "VARIAVEIS_MODELO",
    "AUTOVALOR",
    "PROPORCAO_AUTOVALOR",
    "INDICE_CONDICAO",
    "SINGULAR",
)


def _validate_binary_flags(
    frame: pd.DataFrame,
    flags: list[str] | tuple[str, ...],
) -> pd.DataFrame:
    if not flags:
        raise ValueError("Informe ao menos uma flag para o diagnóstico.")
    if len(set(flags)) != len(flags):
        raise ValueError("A lista de flags não pode conter duplicidades.")
    missing = [flag for flag in flags if flag not in frame.columns]
    if missing:
        raise ValueError(f"Flags ausentes para diagnóstico multivariado: {missing}")
    values = frame[list(flags)].fillna(0).astype(int)
    invalid = ~values.isin([0, 1])
    if invalid.any().any():
        columns = invalid.any(axis=0)
        bad = columns.index[columns].tolist()
        raise ValueError(f"Flags devem conter apenas 0/1: {bad}")
    return values


def _eligible_names(eligibility: pd.DataFrame) -> list[str]:
    return eligibility.loc[
        eligibility["ELEGIVEL_PCA_VIF"].fillna(False), "REGRA"
    ].astype(str).tolist()


def variance_inflation_factors(
    frame: pd.DataFrame,
    flags: list[str] | tuple[str, ...],
    unit: str,
    *,
    kind: str = "TRILHA",
    min_positives: int = MIN_POSITIVES_STATISTICAL,
    min_negatives: int = MIN_NEGATIVES_STATISTICAL,
    tolerance: float = 1e-12,
) -> pd.DataFrame:
    """Calcula VIF por regressão auxiliar OLS sem excluir flags raras silenciosamente."""
    if tolerance <= 0:
        raise ValueError("tolerance deve ser positiva.")

    values = _validate_binary_flags(frame, flags)
    eligibility = evaluate_flag_eligibility(
        values,
        list(flags),
        unit,
        min_positives=min_positives,
        min_negatives=min_negatives,
    )
    eligible = _eligible_names(eligibility)
    eligibility_map = eligibility.set_index("REGRA")

    rows: list[dict[str, object]] = []
    for flag in flags:
        base = eligibility_map.loc[flag]
        status_eligibility = str(base["ELEGIBILIDADE_DIAGNOSTICO_ESTATISTICO"])
        row: dict[str, object] = {
            "UNIDADE_ANALISE": unit,
            "TIPO": kind,
            "REGRA_OU_FAMILIA": flag,
            "N_UNIVERSO": len(values),
            "N_POSITIVOS": int(base["N_POSITIVOS"]),
            "N_NEGATIVOS": int(base["N_NEGATIVOS"]),
            "PREVALENCIA": float(base["PREVALENCIA"]) if len(values) else np.nan,
            "ELEGIBILIDADE_DIAGNOSTICO_ESTATISTICO": status_eligibility,
            "N_VARIAVEIS_ELEGIVEIS_MODELO": len(eligible),
            "R2_AUXILIAR": np.nan,
            "TOLERANCIA": np.nan,
            "VIF": np.nan,
            "STATUS_VIF": f"NAO_CALCULADO_{status_eligibility}",
        }

        if flag not in eligible:
            rows.append(row)
            continue

        other_flags = [candidate for candidate in eligible if candidate != flag]
        if not other_flags:
            r2 = 0.0
        else:
            y = values[flag].to_numpy(dtype=float)
            x = values[other_flags].to_numpy(dtype=float)
            design = np.column_stack([np.ones(len(x), dtype=float), x])
            coefficients, *_ = np.linalg.lstsq(design, y, rcond=None)
            fitted = design @ coefficients
            ss_res = float(np.square(y - fitted).sum())
            ss_tot = float(np.square(y - y.mean()).sum())
            if ss_tot <= tolerance:
                rows.append(row)
                continue
            r2 = 1.0 - (ss_res / ss_tot)
            r2 = float(np.clip(r2, 0.0, 1.0))

        if 1.0 - r2 <= tolerance:
            vif = np.inf
            inv_vif = 0.0
            status_vif = "DEPENDENCIA_LINEAR_PERFEITA"
        else:
            inv_vif = 1.0 - r2
            vif = 1.0 / inv_vif
            status_vif = "CALCULADO"

        row["R2_AUXILIAR"] = r2
        row["TOLERANCIA"] = inv_vif
        row["VIF"] = vif
        row["STATUS_VIF"] = status_vif
        rows.append(row)

    return pd.DataFrame(rows, columns=VIF_COLUMNS)


def condition_indices(
    frame: pd.DataFrame,
    flags: list[str] | tuple[str, ...],
    unit: str,
    *,
    kind: str = "TRILHA",
    min_positives: int = MIN_POSITIVES_STATISTICAL,
    min_negatives: int = MIN_NEGATIVES_STATISTICAL,
    tolerance: float = 1e-12,
) -> pd.DataFrame:
    """Calcula autovalores e índices de condição na matriz de correlação padronizada."""
    if tolerance <= 0:
        raise ValueError("tolerance deve ser positiva.")

    values = _validate_binary_flags(frame, flags)
    eligibility = evaluate_flag_eligibility(
        values,
        list(flags),
        unit,
        min_positives=min_positives,
        min_negatives=min_negatives,
    )
    eligible = _eligible_names(eligibility)
    if not eligible:
        return pd.DataFrame(columns=CONDITION_COLUMNS)

    x = values[eligible].to_numpy(dtype=float)
    means = x.mean(axis=0)
    scales = x.std(axis=0, ddof=0)
    if np.any(scales <= tolerance):
        raise AssertionError("Elegibilidade inconsistente: variável sem variação entrou no modelo.")

    z = (x - means) / scales
    correlation = (z.T @ z) / len(z)
    correlation = (correlation + correlation.T) / 2.0

    eigenvalues = np.linalg.eigvalsh(correlation)[::-1]
    eigenvalues = np.where(np.abs(eigenvalues) <= tolerance, 0.0, eigenvalues)
    eigenvalues = np.maximum(eigenvalues, 0.0)
    largest = float(eigenvalues[0]) if len(eigenvalues) else np.nan
    total = float(eigenvalues.sum())

    rows: list[dict[str, object]] = []
    for index, eigenvalue in enumerate(eigenvalues, start=1):
        singular = bool(eigenvalue <= tolerance)
        condition_index = np.inf if singular else float(np.sqrt(largest / eigenvalue))
        rows.append(
            {
                "UNIDADE_ANALISE": unit,
                "TIPO": kind,
                "COMPONENTE": f"D{index}",
                "N_UNIVERSO": len(values),
                "N_VARIAVEIS_ELEGIVEIS_MODELO": len(eligible),
                "VARIAVEIS_MODELO": ",".join(eligible),
                "AUTOVALOR": float(eigenvalue),
                "PROPORCAO_AUTOVALOR": float(eigenvalue / total) if total else np.nan,
                "INDICE_CONDICAO": condition_index,
                "SINGULAR": singular,
            }
        )
    return pd.DataFrame(rows, columns=CONDITION_COLUMNS)


def multicollinearity_diagnostics(
    frame: pd.DataFrame,
    flags: list[str] | tuple[str, ...],
    unit: str,
    *,
    kind: str = "TRILHA",
    min_positives: int = MIN_POSITIVES_STATISTICAL,
    min_negatives: int = MIN_NEGATIVES_STATISTICAL,
) -> dict[str, pd.DataFrame]:
    """Entrega elegibilidade, VIF e índices de condição sob o mesmo contrato."""
    eligibility = evaluate_flag_eligibility(
        _validate_binary_flags(frame, flags),
        list(flags),
        unit,
        min_positives=min_positives,
        min_negatives=min_negatives,
    )
    eligibility = eligibility.rename(columns={"REGRA": "REGRA_OU_FAMILIA"})
    eligibility.insert(1, "TIPO", kind)

    return {
        "eligibility": eligibility,
        "vif": variance_inflation_factors(
            frame,
            flags,
            unit,
            kind=kind,
            min_positives=min_positives,
            min_negatives=min_negatives,
        ),
        "condition": condition_indices(
            frame,
            flags,
            unit,
            kind=kind,
            min_positives=min_positives,
            min_negatives=min_negatives,
        ),
    }


def multicollinearity_by_group(
    frame: pd.DataFrame,
    flags: list[str] | tuple[str, ...],
    unit: str,
    group_column: str,
    *,
    kind: str = "TRILHA",
    min_positives: int = MIN_POSITIVES_STATISTICAL,
    min_negatives: int = MIN_NEGATIVES_STATISTICAL,
) -> dict[str, pd.DataFrame]:
    """Repete o diagnóstico por estrato, preservando o valor explícito do recorte."""
    if group_column not in frame.columns:
        raise ValueError(f"Coluna de recorte ausente: {group_column}")

    buckets: dict[str, list[pd.DataFrame]] = {
        "eligibility": [],
        "vif": [],
        "condition": [],
    }
    for group_value, group in frame.groupby(group_column, dropna=True, sort=True):
        diagnostics = multicollinearity_diagnostics(
            group,
            flags,
            unit,
            kind=kind,
            min_positives=min_positives,
            min_negatives=min_negatives,
        )
        for name, table in diagnostics.items():
            piece = table.copy()
            piece["RECORTE_COLUNA"] = group_column
            piece["RECORTE_VALOR"] = str(group_value)
            buckets[name].append(piece)

    return {
        name: pd.concat(pieces, ignore_index=True) if pieces else pd.DataFrame()
        for name, pieces in buckets.items()
    }
