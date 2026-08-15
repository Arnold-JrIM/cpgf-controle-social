import plotly.express as px
import streamlit as st

from cpgf.dashboard.components import (
    BLUE,
    ORANGE,
    apply_page_style,
    page_header,
    style_plotly,
)
from cpgf.dashboard.data import top_ugs, ug_exposure_distribution
from cpgf.dashboard.filters import sidebar_filters
from cpgf.dashboard.formatting import format_currency
from cpgf.dashboard.runtime import require_dashboard_context

st.set_page_config(page_title="Distribuição Territorial · CPGF", page_icon="🗺️", layout="wide")
apply_page_style()
page_header(
    "Distribuição territorial — cobertura por UG",
    "O Serving 1.5.0 já incorpora a dimensão Geo 1.1.0 (UG → UF). "
    "Nesta etapa, a página mantém a exploração por Unidade Gestora; o mapa estadual será "
    "habilitado na camada visual seguinte, consumindo os agregados territoriais já validados.",
)

context = require_dashboard_context()
filters = sidebar_filters(context, key_prefix="territory")

st.info(
    "A UF disponível no Serving 1.5.0 representa a localização cadastral da Unidade Gestora, "
    "e não necessariamente o local físico em que a compra, saque ou operação ocorreu."
)

ranking = top_ugs(context, filters, limit=25)
left, right = st.columns([1.2, 1])

with left:
    chart = ranking.sort_values("ANOS_COM_SINAL").tail(15)
    fig = px.bar(
        chart,
        x="ANOS_COM_SINAL",
        y="CODIGO_UG",
        orientation="h",
        hover_data=["OPERACOES", "VALOR_TOTAL", "SOMA_TRILHAS_ATIVAS"],
        labels={"ANOS_COM_SINAL": "Anos com sinal", "CODIGO_UG": "UG"},
        title="Recorrência de sinais por Unidade Gestora",
    )
    fig.update_traces(marker_color=ORANGE)
    st.plotly_chart(style_plotly(fig), width="stretch")

with right:
    exposure = ug_exposure_distribution(context, filters)
    fig = px.bar(
        exposure,
        x="DECIL",
        y="UG_ANO",
        hover_data=["OPERACOES", "VALOR_TOTAL", "UG_ANO_SINALIZADAS"],
        labels={"DECIL": "Decil anual de exposição", "UG_ANO": "UG-ano"},
        title="Distribuição por decil de exposição anual",
    )
    fig.update_traces(marker_color=BLUE)
    st.plotly_chart(style_plotly(fig), width="stretch")

st.subheader("Detalhamento das UGs priorizadas pela recorrência")
table = ranking.copy()
if not table.empty:
    table["VALOR_TOTAL"] = table["VALOR_TOTAL"].map(format_currency)
    st.dataframe(table, width="stretch", hide_index=True)
