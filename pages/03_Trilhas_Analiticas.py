import plotly.express as px
import streamlit as st

from cpgf.dashboard.components import (
    ORANGE,
    apply_page_style,
    page_header,
    render_disclaimer,
    style_plotly,
)
from cpgf.dashboard.data import (
    TRAIL_LABELS,
    supplier_exposure_distribution,
    top_suppliers,
    trail_prevalence,
    ug_signal_distribution,
)
from cpgf.dashboard.filters import sidebar_filters
from cpgf.dashboard.formatting import format_currency, format_integer, format_percent
from cpgf.dashboard.runtime import require_dashboard_context

st.set_page_config(page_title="Trilhas Analíticas · CPGF", page_icon="🔎", layout="wide")
apply_page_style()
page_header(
    "Trilhas Analíticas",
    "Incidência das nove trilhas congeladas na versão de Regras 1.2.0, sempre interpretadas "
    "como mecanismos de triagem e não como confirmação de irregularidade.",
)
render_disclaimer()

context = require_dashboard_context()
filters = sidebar_filters(context, key_prefix="trails")

trails = trail_prevalence(context, filters)
left, right = st.columns([1.25, 1])

with left:
    ordered = trails.sort_values("UNIDADES_SINALIZADAS")
    fig = px.bar(
        ordered,
        x="UNIDADES_SINALIZADAS",
        y="CODIGO",
        orientation="h",
        hover_data=["TRILHA", "TIPO", "PREVALENCIA"],
        labels={"UNIDADES_SINALIZADAS": "UG-ano sinalizadas", "CODIGO": "Trilha"},
        title="Incidência dos sinais por trilha",
    )
    fig.update_traces(marker_color=ORANGE)
    st.plotly_chart(style_plotly(fig), use_container_width=True)

with right:
    distribution = ug_signal_distribution(context, filters)
    fig = px.bar(
        distribution,
        x="N_TRILHAS",
        y="UNIDADES",
        labels={"N_TRILHAS": "Número de trilhas ativas", "UNIDADES": "UG-ano"},
        title="Quantidade de trilhas simultaneamente ativas",
    )
    fig.update_traces(marker_color=ORANGE)
    st.plotly_chart(style_plotly(fig), use_container_width=True)

st.subheader("Dicionário das trilhas")
for code, label in TRAIL_LABELS.items():
    row = trails.loc[trails["CODIGO"].eq(code)].iloc[0]
    with st.expander(f"{code} · {label}"):
        st.write(
            f"Tipo no Motor 1.3.2: **{row['TIPO']}**. "
            f"No recorte atual, a trilha aparece em "
            f"**{format_integer(row['UNIDADES_SINALIZADAS'])}** unidades UG-ano "
            f"({format_percent(row['PREVALENCIA'])})."
        )

st.subheader("Fornecedores com maior recorrência de sinais")
st.caption(
    "A versão atual do serving preserva a chave analítica do fornecedor; a dimensão nominal "
    "será incorporada apenas quando houver materialização curada da dimensão cadastral."
)
suppliers = top_suppliers(context, filters, limit=20).copy()
if not suppliers.empty:
    suppliers["VALOR_COMPRAS"] = suppliers["VALOR_COMPRAS"].map(format_currency)
    st.dataframe(suppliers, use_container_width=True, hide_index=True)

st.subheader("Exposição dos fornecedores")
exposure = supplier_exposure_distribution(context, filters)
st.dataframe(exposure, use_container_width=True, hide_index=True)
