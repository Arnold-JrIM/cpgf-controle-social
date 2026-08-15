import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from cpgf.dashboard.components import (
    BLUE,
    ORANGE,
    apply_page_style,
    page_header,
    style_plotly,
)
from cpgf.dashboard.data import diagnostic_table
from cpgf.dashboard.runtime import require_dashboard_context

st.set_page_config(page_title="Diagnóstico do Motor · CPGF", page_icon="🧪", layout="wide")
apply_page_style()
page_header(
    "Diagnóstico do Motor",
    "Sobreposição, contribuição marginal e diagnósticos multivariados que documentam como "
    "as trilhas se relacionam sem produzir exclusão automática de regras.",
)

context = require_dashboard_context()

overlap = diagnostic_table(context, "overlap_ug_trails")
marginal = diagnostic_table(context, "marginal_ug_trails")

left, right = st.columns([1.25, 1])

with left:
    rules = sorted(set(overlap["REGRA_A"]).union(overlap["REGRA_B"]))
    matrix = pd.DataFrame(1.0, index=rules, columns=rules)
    for row in overlap.itertuples(index=False):
        matrix.loc[row.REGRA_A, row.REGRA_B] = row.JACCARD
        matrix.loc[row.REGRA_B, row.REGRA_A] = row.JACCARD
    fig = go.Figure(
        data=go.Heatmap(
            z=matrix.values,
            x=matrix.columns,
            y=matrix.index,
            colorbar_title="Jaccard",
            colorscale=[[0, "#F4F6F8"], [1, ORANGE]],
            zmin=0,
            zmax=1,
            hovertemplate="%{y} × %{x}<br>Jaccard=%{z:.3f}<extra></extra>",
        )
    )
    fig.update_layout(title="Sobreposição entre trilhas — Jaccard")
    st.plotly_chart(style_plotly(fig, height=430, legend=False), width="stretch")

with right:
    plot = marginal.sort_values("CONTRIBUICAO_MARGINAL_PCT")
    fig = px.bar(
        plot,
        x="CONTRIBUICAO_MARGINAL_PCT",
        y="REGRA_OU_FAMILIA",
        orientation="h",
        hover_data=["N_SINALIZADOS", "N_EXCLUSIVOS", "PERDA_UNIDADES_SE_REMOVER"],
        labels={
            "CONTRIBUICAO_MARGINAL_PCT": "Contribuição marginal",
            "REGRA_OU_FAMILIA": "Trilha",
        },
        title="Contribuição marginal das trilhas",
    )
    fig.update_traces(marker_color=BLUE)
    fig.update_xaxes(tickformat=".0%")
    st.plotly_chart(style_plotly(fig, height=430, legend=False), width="stretch")

st.markdown(
    """
    **Leitura metodológica.** Sobreposição elevada não implica redundância normativa.
    A contribuição marginal informa quantas unidades deixariam a união do motor se uma
    trilha fosse retirada; a decisão de manter, revisar ou remover uma trilha depende também
    de seu fundamento normativo ou científico.
    """
)

with st.expander("VIF e elegibilidade estatística"):
    vif = diagnostic_table(context, "multicollinearity_ug_trails_vif")
    st.dataframe(vif, width="stretch", hide_index=True)

with st.expander("Índices de condição"):
    condition = diagnostic_table(context, "multicollinearity_ug_trails_condition")
    st.dataframe(condition, width="stretch", hide_index=True)

with st.expander("PCA — componentes e cargas"):
    components = diagnostic_table(context, "pca_ug_trails_components")
    loadings = diagnostic_table(context, "pca_ug_trails_loadings")
    st.markdown("**Componentes**")
    st.dataframe(components, width="stretch", hide_index=True)
    st.markdown("**Cargas**")
    st.dataframe(loadings, width="stretch", hide_index=True)
