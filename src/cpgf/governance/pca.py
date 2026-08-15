from __future__ import annotations

import numpy as np
import pandas as pd

from .eligibility import (
    MIN_NEGATIVES_STATISTICAL,
    MIN_POSITIVES_STATISTICAL,
    evaluate_flag_eligibility,
)

PCA_COMPONENT_COLUMNS: tuple[str, ...] = (
    "UNIDADE_ANALISE",
    "TIPO",
    "COMPONENTE",
    "N_UNIVERSO",
    "N_VARIAVEIS_ELEGIVEIS_MODELO",
    "VARIAVEIS_MODELO",
    "AUTOVALOR",
    "VARIANCIA_EXPLICADA",
    "VARIANCIA_EXPLICADA_ACUMULADA",
)

PCA_LOADING_COLUMNS: tuple[str, ...] = (
    "UNIDADE_ANALISE",
    "TIPO",
    "REGRA_OU_FAMILIA",
    "COMPONENTE",
    "PESO_COMPONENTE",
    "CARGA_CORRELACAO",
    "CARGA_QUADRADA",
    "COMUNALIDADE_ACUMULADA",
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
        raise ValueError(f"Flags ausentes para PCA: {missing}")
    values = frame[list(flags)].fillna(0).astype(int)
    invalid = ~values.isin([0, 1])
    if invalid.any().any():
        columns = invalid.any(axis=0)
        bad = columns.index[columns].tolist()
        raise ValueError(f"Flags devem conter apenas 0/1: {bad}")
    return values


def _orient_eigenvectors(eigenvectors: np.ndarray) -> np.ndarray:
    """Fixa o sinal de cada componente para tornar a saída reprodutível."""
    oriented = eigenvectors.copy()
    for column in range(oriented.shape[1]):
        vector = oriented[:, column]
        pivot = int(np.argmax(np.abs(vector)))
        if vector[pivot] < 0:
            oriented[:, column] *= -1
    return oriented


def principal_component_diagnostics(
    frame: pd.DataFrame,
    flags: list[str] | tuple[str, ...],
    unit: str,
    *,
    kind: str = "TRILHA",
    min_positives: int = MIN_POSITIVES_STATISTICAL,
    min_negatives: int = MIN_NEGATIVES_STATISTICAL,
    tolerance: float = 1e-12,
) -> dict[str, pd.DataFrame]:
    """Executa PCA descritiva na matriz de correlação das flags binárias elegíveis."""
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
    eligibility = eligibility.rename(columns={"REGRA": "REGRA_OU_FAMILIA"})
    eligibility.insert(1, "TIPO", kind)

    eligible = eligibility.loc[
        eligibility["ELEGIVEL_PCA_VIF"].fillna(False), "REGRA_OU_FAMILIA"
    ].astype(str).tolist()

    if not eligible:
        return {
            "eligibility": eligibility,
            "components": pd.DataFrame(columns=PCA_COMPONENT_COLUMNS),
            "loadings": pd.DataFrame(columns=PCA_LOADING_COLUMNS),
        }

    x = values[eligible].to_numpy(dtype=float)
    means = x.mean(axis=0)
    scales = x.std(axis=0, ddof=0)
    if np.any(scales <= tolerance):
        raise AssertionError("Elegibilidade inconsistente: variável sem variação entrou na PCA.")

    z = (x - means) / scales
    correlation = (z.T @ z) / len(z)
    correlation = (correlation + correlation.T) / 2.0

    eigenvalues, eigenvectors = np.linalg.eigh(correlation)
    order = np.argsort(eigenvalues)[::-1]
    eigenvalues = eigenvalues[order]
    eigenvectors = eigenvectors[:, order]
    eigenvalues = np.where(np.abs(eigenvalues) <= tolerance, 0.0, eigenvalues)
    eigenvalues = np.maximum(eigenvalues, 0.0)
    eigenvectors = _orient_eigenvectors(eigenvectors)

    total = float(eigenvalues.sum())
    explained = eigenvalues / total if total else np.full(len(eigenvalues), np.nan)
    cumulative = np.cumsum(explained) if total else np.full(len(eigenvalues), np.nan)

    components = pd.DataFrame(
        {
            "UNIDADE_ANALISE": unit,
            "TIPO": kind,
            "COMPONENTE": [f"PC{index}" for index in range(1, len(eigenvalues) + 1)],
            "N_UNIVERSO": len(values),
            "N_VARIAVEIS_ELEGIVEIS_MODELO": len(eligible),
            "VARIAVEIS_MODELO": ",".join(eligible),
            "AUTOVALOR": eigenvalues.astype(float),
            "VARIANCIA_EXPLICADA": explained.astype(float),
            "VARIANCIA_EXPLICADA_ACUMULADA": cumulative.astype(float),
        },
        columns=PCA_COMPONENT_COLUMNS,
    )

    correlation_loadings = eigenvectors * np.sqrt(eigenvalues)
    loading_rows: list[dict[str, object]] = []
    for variable_index, variable in enumerate(eligible):
        communality = 0.0
        for component_index in range(len(eigenvalues)):
            weight = float(eigenvectors[variable_index, component_index])
            loading = float(correlation_loadings[variable_index, component_index])
            squared = loading * loading
            communality += squared
            loading_rows.append(
                {
                    "UNIDADE_ANALISE": unit,
                    "TIPO": kind,
                    "REGRA_OU_FAMILIA": variable,
                    "COMPONENTE": f"PC{component_index + 1}",
                    "PESO_COMPONENTE": weight,
                    "CARGA_CORRELACAO": loading,
                    "CARGA_QUADRADA": squared,
                    "COMUNALIDADE_ACUMULADA": communality,
                }
            )

    return {
        "eligibility": eligibility,
        "components": components,
        "loadings": pd.DataFrame(loading_rows, columns=PCA_LOADING_COLUMNS),
    }


def pca_by_group(
    frame: pd.DataFrame,
    flags: list[str] | tuple[str, ...],
    unit: str,
    group_column: str,
    *,
    kind: str = "TRILHA",
    min_positives: int = MIN_POSITIVES_STATISTICAL,
    min_negatives: int = MIN_NEGATIVES_STATISTICAL,
) -> dict[str, pd.DataFrame]:
    """Repete a PCA por estrato de exposição sem misturar os universos."""
    if group_column not in frame.columns:
        raise ValueError(f"Coluna de recorte ausente: {group_column}")

    buckets: dict[str, list[pd.DataFrame]] = {
        "eligibility": [],
        "components": [],
        "loadings": [],
    }
    for group_value, group in frame.groupby(group_column, dropna=True, sort=True):
        diagnostics = principal_component_diagnostics(
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
