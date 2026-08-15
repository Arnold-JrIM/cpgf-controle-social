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
    "Nesta versão, a distribuição é apresentada por Unidade Gestora. O mapa por UF/município "
    "será ativado somente quando a dimensão geográfica oficial estiver materializada no serving.",
)

context = require_dashboard_context()
filters = sidebar_filters(context, key_prefix="territory")

st.info(
    "O Serving 1.4.0 não contém uma dimensão oficial UG → UF/município. "
    "Para preservar rastreabilidade, a aplicação não infere localização a partir do código da UG."
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
    st.plotly_chart(style_plotly(fig), use_container_width=True)

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
    st.plotly_chart(style_plotly(fig), use_container_width=True)

st.subheader("Detalhamento das UGs priorizadas pela recorrência")
table = ranking.copy()
if not table.empty:
    table["VALOR_TOTAL"] = table["VALOR_TOTAL"].map(format_currency)
    st.dataframe(table, use_container_width=True, hide_index=True)
