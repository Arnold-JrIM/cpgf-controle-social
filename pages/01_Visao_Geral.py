import plotly.express as px
import streamlit as st

from cpgf.dashboard.components import (
    ORANGE,
    apply_page_style,
    page_header,
    render_disclaimer,
    style_plotly,
)
from cpgf.dashboard.data import annual_overview, overview_summary, top_ugs, trail_prevalence
from cpgf.dashboard.filters import sidebar_filters
from cpgf.dashboard.formatting import format_currency, format_integer, format_percent
from cpgf.dashboard.runtime import require_dashboard_context

st.set_page_config(page_title="Visão Geral · CPGF", page_icon="📊", layout="wide")
apply_page_style()
page_header(
    "Visão Geral",
    "Materialidade, volume de operações e incidência dos sinais analíticos no período selecionado.",
)
render_disclaimer()

context = require_dashboard_context()
filters = sidebar_filters(context, key_prefix="overview")
summary = overview_summary(context, filters)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Valor observado", format_currency(summary["total_value"]))
c2.metric("Operações efetivas", format_integer(summary["operations"]))
c3.metric("Unidades gestoras", format_integer(summary["ugs"]))
c4.metric("Fornecedores observáveis", format_integer(summary["suppliers"]))

c5, c6 = st.columns(2)
ug_rate = summary["signaled_ug_year"] / summary["ug_year"] if summary["ug_year"] else 0
supplier_rate = (
    summary["signaled_supplier_year"] / summary["supplier_year"]
    if summary["supplier_year"]
    else 0
)
c5.metric("UG-ano com sinal", format_percent(ug_rate))
c6.metric("UG-fornecedor-ano com sinal", format_percent(supplier_rate))

annual = annual_overview(context, filters)
left, right = st.columns([1.35, 1])

with left:
    fig = px.area(
        annual,
        x="ANO",
        y="VALOR_TOTAL",
        labels={"ANO": "Ano", "VALOR_TOTAL": "Valor (R$)"},
        title="Evolução anual da materialidade",
    )
    fig.update_traces(line_color=ORANGE, fillcolor="rgba(230,126,34,0.18)")
    st.plotly_chart(style_plotly(fig), width="stretch")

with right:
    trails = trail_prevalence(context, filters)
    trails = trails.sort_values("UNIDADES_SINALIZADAS", ascending=True)
    fig = px.bar(
        trails,
        x="UNIDADES_SINALIZADAS",
        y="CODIGO",
        orientation="h",
        hover_data=["TRILHA", "TIPO", "PREVALENCIA"],
        labels={"UNIDADES_SINALIZADAS": "UG-ano sinalizadas", "CODIGO": "Trilha"},
        title="Incidência por trilha",
    )
    fig.update_traces(marker_color=ORANGE)
    st.plotly_chart(style_plotly(fig), width="stretch")

st.subheader("Unidades gestoras com maior recorrência de sinais")
ranking = top_ugs(context, filters, limit=15).copy()
if not ranking.empty:
    ranking["VALOR_TOTAL"] = ranking["VALOR_TOTAL"].map(format_currency)
    st.dataframe(
        ranking.rename(
            columns={
                "CODIGO_UG": "UG",
                "ANOS_OBSERVADOS": "Anos observados",
                "OPERACOES": "Operações",
                "VALOR_TOTAL": "Valor",
                "ANOS_COM_SINAL": "Anos com sinal",
                "SOMA_TRILHAS_ATIVAS": "Soma de trilhas ativas",
            }
        ),
        width="stretch",
        hide_index=True,
    )
