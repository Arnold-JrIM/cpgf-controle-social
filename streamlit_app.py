import plotly.express as px
import streamlit as st

from cpgf.dashboard.components import (
    ORANGE,
    apply_page_style,
    page_header,
    render_disclaimer,
    style_plotly,
)
from cpgf.dashboard.data import DashboardFilter, annual_overview, overview_summary
from cpgf.dashboard.formatting import format_currency, format_integer, format_percent
from cpgf.dashboard.runtime import require_dashboard_context
from cpgf.version import APP_VERSION, MOTOR_VERSION, RULES_VERSION, SERVING_VERSION

st.set_page_config(
    page_title="CPGF — Controle Social",
    page_icon="💳",
    layout="wide",
    initial_sidebar_state="expanded",
)
apply_page_style()

page_header(
    "CPGF — Controle Social Orientado por Dados e IA",
    "Uma aplicação pública para transformar dados abertos do Cartão de Pagamento do "
    "Governo Federal em informações compreensíveis, rastreáveis e úteis à participação cidadã.",
)
render_disclaimer()

context = require_dashboard_context()
years = sorted(
    context.repository.read("matrix_ug_year", limit=100_000)["ANO"].dropna().astype(int).unique()
)
filters = DashboardFilter(year_start=int(years[0]), year_end=int(years[-1]))
summary = overview_summary(context, filters)

st.caption(
    f"Aplicação {APP_VERSION} · Regras {RULES_VERSION} · "
    f"Motor/Governança {MOTOR_VERSION} · Serving {SERVING_VERSION}"
)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Operações efetivas", format_integer(summary["operations"]))
c2.metric("Valor observado", format_currency(summary["total_value"]))
c3.metric("Unidades gestoras", format_integer(summary["ugs"]))
share = (
    summary["signaled_ug_year"] / summary["ug_year"]
    if summary["ug_year"]
    else 0.0
)
c4.metric("UG-ano com ao menos 1 sinal", format_percent(share))

annual = annual_overview(context, filters)
fig = px.line(
    annual,
    x="ANO",
    y="VALOR_TOTAL",
    markers=True,
    labels={"ANO": "Ano", "VALOR_TOTAL": "Valor total (R$)"},
    title="Evolução anual do valor observado",
)
fig.update_traces(line_color=ORANGE, marker_color=ORANGE)
style_plotly(fig, height=360, legend=False)
st.plotly_chart(fig, width="stretch")

st.markdown(
    """
    <div class="cpgf-neutral">
    <strong>Navegue pelo menu lateral.</strong> A Visão Geral apresenta materialidade e
    recorrência; Trilhas Analíticas mostra a incidência dos sinais; Diagnóstico do Motor
    documenta sobreposição e contribuição marginal; Metodologia explica os limites de uso.
    </div>
    """,
    unsafe_allow_html=True,
)
