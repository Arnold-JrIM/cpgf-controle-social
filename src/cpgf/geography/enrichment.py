from __future__ import annotations

import pandas as pd

from .ug_dimension import UFS_BRASIL


def extract_year_with_fallback(staged: pd.DataFrame) -> pd.Series:
    """Replica a referência EXTRATO do Geo 1.1.0 sem alterar a Preparation 1.1.0."""
    year = staged["ANO_EXTRATO_REF"].astype("Int64").copy()
    if "COMPETENCIA_ARQUIVO" in staged.columns:
        fallback = pd.to_numeric(
            staged["COMPETENCIA_ARQUIVO"].astype("string").str.slice(0, 4),
            errors="coerce",
        ).astype("Int64")
        year = year.fillna(fallback)
    return year


def build_geographic_projection(
    staged: pd.DataFrame,
    dimension: pd.DataFrame,
) -> pd.DataFrame:
    """Produz somente as colunas necessárias aos agregados territoriais do Geo 1.1.0."""
    columns = [
        "UG_ID",
        "ANO_TRANSACAO",
        "DATA_DT",
        "VALOR_CENTAVOS",
        "EH_COMPRA_EFETIVA",
        "EH_SAQUE_EFETIVO",
        "EH_AJUSTE_CONTESTACAO",
        "EH_SIGILOSO",
    ]
    geo = staged[columns].copy()
    geo["ANO_EXTRATO_REF"] = extract_year_with_fallback(staged)
    geo = geo.merge(
        dimension[["UG_ID", "UF_UG"]],
        how="left",
        on="UG_ID",
        validate="many_to_one",
    )
    if geo["UF_UG"].isna().any():
        raise ValueError("Enriquecimento geográfico deixou registros CPGF sem UF da UG.")

    positive = geo["VALOR_CENTAVOS"].gt(0).fillna(False)
    non_adjustment = ~geo["EH_AJUSTE_CONTESTACAO"].fillna(False)
    geo["GEO_POSITIVA_NAO_AJUSTE"] = positive & non_adjustment
    geo["GEO_COMPRA_OBSERVAVEL"] = geo["GEO_POSITIVA_NAO_AJUSTE"] & geo[
        "EH_COMPRA_EFETIVA"
    ].fillna(False)
    geo["GEO_SAQUE_OBSERVAVEL"] = geo["GEO_POSITIVA_NAO_AJUSTE"] & geo[
        "EH_SAQUE_EFETIVO"
    ].fillna(False)
    geo["GEO_SIGILOSO"] = geo["GEO_POSITIVA_NAO_AJUSTE"] & geo["EH_SIGILOSO"].fillna(False)
    geo["GEO_DATA_TRANSACAO_OBSERVAVEL"] = geo["DATA_DT"].notna()
    geo["GEO_UF_BRASIL"] = geo["UF_UG"].isin(UFS_BRASIL)
    return geo
