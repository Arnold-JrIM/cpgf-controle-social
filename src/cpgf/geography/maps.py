from __future__ import annotations

import pandas as pd

# Âncoras cartográficas usadas somente para posicionamento visual das 27 UFs.
# Os valores analíticos do mapa vêm exclusivamente do Serving 1.5.0 / Geo 1.1.0.
# Referência das coordenadas: kelvins/Municipios-Brasileiros, csv/estados.csv.
_UF_PLOT_ANCHORS = (
    ("RO", "Rondônia", "Norte", -10.83, -63.34),
    ("AC", "Acre", "Norte", -8.77, -70.55),
    ("AM", "Amazonas", "Norte", -3.47, -65.10),
    ("RR", "Roraima", "Norte", 1.99, -61.33),
    ("PA", "Pará", "Norte", -3.79, -52.48),
    ("AP", "Amapá", "Norte", 1.41, -51.77),
    ("TO", "Tocantins", "Norte", -9.46, -48.26),
    ("MA", "Maranhão", "Nordeste", -5.42, -45.44),
    ("PI", "Piauí", "Nordeste", -6.60, -42.28),
    ("CE", "Ceará", "Nordeste", -5.20, -39.53),
    ("RN", "Rio Grande do Norte", "Nordeste", -5.81, -36.59),
    ("PB", "Paraíba", "Nordeste", -7.28, -36.72),
    ("PE", "Pernambuco", "Nordeste", -8.38, -37.86),
    ("AL", "Alagoas", "Nordeste", -9.62, -36.82),
    ("SE", "Sergipe", "Nordeste", -10.57, -37.45),
    ("BA", "Bahia", "Nordeste", -13.29, -41.71),
    ("MG", "Minas Gerais", "Sudeste", -18.10, -44.38),
    ("ES", "Espírito Santo", "Sudeste", -19.19, -40.34),
    ("RJ", "Rio de Janeiro", "Sudeste", -22.25, -42.66),
    ("SP", "São Paulo", "Sudeste", -22.19, -48.79),
    ("PR", "Paraná", "Sul", -24.89, -51.55),
    ("SC", "Santa Catarina", "Sul", -27.45, -50.95),
    ("RS", "Rio Grande do Sul", "Sul", -30.17, -53.50),
    ("MS", "Mato Grosso do Sul", "Centro-Oeste", -20.51, -54.54),
    ("MT", "Mato Grosso", "Centro-Oeste", -12.64, -55.42),
    ("GO", "Goiás", "Centro-Oeste", -15.98, -49.86),
    ("DF", "Distrito Federal", "Centro-Oeste", -15.83, -47.86),
)


def uf_plot_anchors() -> pd.DataFrame:
    """Retorna âncoras visuais para as 27 UFs, sem finalidade analítica."""
    return pd.DataFrame(
        _UF_PLOT_ANCHORS,
        columns=["UF", "NOME_UF", "REGIAO", "LATITUDE", "LONGITUDE"],
    )


def attach_uf_plot_anchors(
    frame: pd.DataFrame,
    *,
    uf_column: str = "UF",
) -> pd.DataFrame:
    """Acrescenta coordenadas de plotagem e exige cobertura integral das UFs informadas."""
    if uf_column not in frame.columns:
        raise ValueError(f"Coluna de UF ausente: {uf_column}.")

    anchors = uf_plot_anchors()
    result = frame.merge(
        anchors,
        how="left",
        left_on=uf_column,
        right_on="UF",
        validate="many_to_one",
        suffixes=("", "_ANCORA"),
    )
    missing = sorted(
        result.loc[result["LATITUDE"].isna(), uf_column]
        .dropna()
        .astype("string")
        .unique()
        .tolist()
    )
    if missing:
        raise ValueError(f"UFs sem âncora cartográfica: {missing}.")
    if uf_column != "UF" and "UF_ANCORA" in result.columns:
        result = result.drop(columns=["UF_ANCORA"])
    return result
