import plotly.express as px
import streamlit as st

from cpgf.dashboard.components import (
    ORANGE,
    apply_page_style,
    page_header,
    render_disclaimer,
    style_plotly,
)
from cpgf.dashboard.data import top_suppliers, top_ugs, trail_prevalence
from cpgf.dashboard.filters import sidebar_filters
from cpgf.dashboard.formatting import format_currency
from cpgf.dashboard.runtime import require_dashboard_context

st.set_page_config(page_title="Sinais e Validação · CPGF", page_icon="✅", layout="wide")
apply_page_style()
page_header(
    "Sinais e Validação",
    "Uma camada de triagem para orientar a verificação documental. A interface destaca "
    "recorrência e materialidade sem transformar sinal analítico em conclusão automática.",
)
render_disclaimer()

context = require_dashboard_context()
filters = sidebar_filters(context, key_prefix="signals")

trails = trail_prevalence(context, filters)
fig = px.bar(
    trails.sort_values("PREVALENCIA"),
    x="PREVALENCIA",
    y="CODIGO",
    orientation="h",
    hover_data=["TRILHA", "UNIDADES_SINALIZADAS", "TIPO"],
    labels={"PREVALENCIA": "Prevalência em UG-ano", "CODIGO": "Trilha"},
    title="Prevalência dos sinais no recorte",
)
fig.update_traces(marker_color=ORANGE)
fig.update_xaxes(tickformat=".0%")
st.plotly_chart(style_plotly(fig, height=390, legend=False), use_container_width=True)

left, right = st.columns(2)
with left:
    st.subheader("UGs com maior recorrência")
    ugs = top_ugs(context, filters, limit=15).copy()
    if not ugs.empty:
        ugs["VALOR_TOTAL"] = ugs["VALOR_TOTAL"].map(format_currency)
        st.dataframe(ugs, use_container_width=True, hide_index=True)

with right:
    st.subheader("Fornecedores com maior recorrência")
    suppliers = top_suppliers(context, filters, limit=15).copy()
    if not suppliers.empty:
        suppliers["VALOR_COMPRAS"] = suppliers["VALOR_COMPRAS"].map(format_currency)
        st.dataframe(suppliers, use_container_width=True, hide_index=True)

st.markdown(
    """
    ### O que significa validar um sinal?
    A validação exige retornar ao contexto da despesa, aos documentos de suporte e às regras
    aplicáveis. O dashboard não atribui status de fraude nem substitui o juízo profissional.
    Na governança do projeto, a confirmação é uma etapa humana e documentada, separada da
    detecção automática.
    """
)
