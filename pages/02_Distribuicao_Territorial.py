import plotly.express as px
import streamlit as st

from cpgf.dashboard.components import (
    BLUE,
    ORANGE,
    apply_page_style,
    page_header,
    style_plotly,
)
from cpgf.dashboard.formatting import format_currency, format_geographic_metric, format_integer
from cpgf.dashboard.runtime import require_dashboard_context
from cpgf.dashboard.territorial import (
    geographic_available_years,
    geographic_metric_catalog,
    geographic_uf_metric,
    territorial_ug_context,
)
from cpgf.geography.maps import attach_uf_plot_anchors

st.set_page_config(page_title="Distribuição Territorial · CPGF", page_icon="🗺️", layout="wide")
apply_page_style()
page_header(
    "Distribuição territorial do CPGF",
    "Mapa estadual construído sobre os agregados Geo 1.1.0 materializados no Serving 1.5.0. "
    "A interface apenas consulta resultados prontos; nenhum enriquecimento é refeito no Streamlit.",
)

context = require_dashboard_context()
catalog = geographic_metric_catalog(context)

reference_labels = {
    "TRANSACAO": "Transação — ano da data observável",
    "EXTRATO": "Extrato — ano de referência do ciclo",
}
control_a, control_b, control_c = st.columns([1.2, 1, 2.2])
with control_a:
    reference = st.selectbox(
        "Referência temporal",
        options=list(reference_labels),
        format_func=reference_labels.get,
        key="territorial_reference",
    )
with control_b:
    years = geographic_available_years(context, reference)
    year = st.selectbox(
        "Ano",
        options=years,
        index=len(years) - 1,
        key="territorial_year",
    )
with control_c:
    eligible = catalog.loc[catalog["REFERENCIA_TEMPORAL"].eq(reference)].copy()
    metric_labels = dict(zip(eligible["METRICA"], eligible["ROTULO"], strict=True))
    principal = eligible.loc[eligible["METRICA_PRINCIPAL"].astype(bool), "METRICA"].tolist()
    default_metric = principal[0] if principal else eligible["METRICA"].iloc[0]
    metric_options = eligible["METRICA"].tolist()
    metric = st.selectbox(
        "Métrica",
        options=metric_options,
        index=metric_options.index(default_metric),
        format_func=metric_labels.get,
        key="territorial_metric",
    )

territorial = geographic_uf_metric(
    context,
    reference=reference,
    year=int(year),
    metric=metric,
)
if territorial.empty:
    st.warning("Não há dados territoriais para a combinação selecionada.")
    st.stop()

territorial = attach_uf_plot_anchors(territorial)
unit = str(territorial["UNIDADE"].iloc[0])
metric_label = str(territorial["ROTULO_METRICA"].iloc[0])
status = str(territorial["STATUS_PERIODO"].iloc[0])
territorial["VALOR_FORMATADO"] = territorial["VALOR_METRICA"].map(
    lambda value: format_geographic_metric(value, unit)
)

st.info(
    "A UF representa a localização cadastral da Unidade Gestora (UG), não necessariamente o "
    "local físico em que a compra, saque ou outra operação ocorreu. As coordenadas no mapa são "
    "somente âncoras de visualização por UF e não participam do cálculo dos indicadores."
)
if status == "PERIODO_PARCIAL":
    st.warning(
        f"{year} é período parcial no snapshot atual. Compare-o com exercícios completos com cautela."
    )

cards = st.columns(4)
cards[0].metric("UFs representadas", format_integer(len(territorial)))
if unit in {"BRL", "CONTAGEM"}:
    aggregate_value = territorial["VALOR_METRICA"].sum()
    cards[1].metric("Total no recorte", format_geographic_metric(aggregate_value, unit))
else:
    median_value = territorial["VALOR_METRICA"].median()
    cards[1].metric("Mediana das UFs", format_geographic_metric(median_value, unit))
top_row = territorial.sort_values("VALOR_METRICA", ascending=False).iloc[0]
cards[2].metric("Maior valor", f"{top_row['UF']} · {top_row['VALOR_FORMATADO']}")
cards[3].metric("Status do período", "Completo" if status == "EXERCICIO_COMPLETO" else "Parcial")

map_col, rank_col = st.columns([1.45, 1])
with map_col:
    fig = px.scatter_geo(
        territorial,
        lat="LATITUDE",
        lon="LONGITUDE",
        size="VALOR_METRICA",
        color="VALOR_METRICA",
        hover_name="NOME_UF",
        custom_data=["UF", "VALOR_FORMATADO", "REGIAO"],
        size_max=42,
        color_continuous_scale=["#dbeafe", BLUE, "#0b1f3a"],
        title=f"{metric_label} por UF · {year}",
    )
    fig.update_traces(
        marker_line_width=0.8,
        marker_line_color="white",
        hovertemplate=(
            "<b>%{hovertext}</b><br>UF: %{customdata[0]}<br>"
            f"{metric_label}: %{{customdata[1]}}<br>Região: %{{customdata[2]}}<extra></extra>"
        ),
    )
    fig.update_geos(
        projection_type="natural earth",
        showcountries=True,
        countrycolor="#cbd5e1",
        showland=True,
        landcolor="#f8fafc",
        showocean=True,
        oceancolor="#ffffff",
        lataxis_range=[-35, 7],
        lonaxis_range=[-75, -32],
        bgcolor="rgba(0,0,0,0)",
    )
    fig.update_layout(coloraxis_colorbar_title="Valor")
    st.plotly_chart(style_plotly(fig), width="stretch")
    st.caption(
        "Mapa de pontos proporcionais: posição cartográfica aproximada da UF; tamanho e intensidade "
        "representam exclusivamente a métrica selecionada no Serving 1.5.0."
    )

with rank_col:
    ranking = territorial.sort_values("VALOR_METRICA", ascending=True).tail(15)
    rank_fig = px.bar(
        ranking,
        x="VALOR_METRICA",
        y="UF",
        orientation="h",
        custom_data=["VALOR_FORMATADO", "NOME_UF"],
        labels={"VALOR_METRICA": metric_label, "UF": "UF"},
        title="Ranking das UFs",
    )
    rank_fig.update_traces(
        marker_color=BLUE,
        hovertemplate=(
            "<b>%{customdata[1]} (%{y})</b><br>"
            f"{metric_label}: %{{customdata[0]}}<extra></extra>"
        ),
    )
    st.plotly_chart(style_plotly(rank_fig), width="stretch")

st.subheader("Contexto das Unidades Gestoras na UF")
uf_order = territorial.sort_values("VALOR_METRICA", ascending=False)["UF"].tolist()
selected_uf = st.selectbox(
    "UF para detalhamento",
    options=uf_order,
    index=0,
    key="territorial_uf_detail",
)
ug_frame = territorial_ug_context(context, uf=selected_uf, year=int(year), limit=50)

st.caption(
    "O detalhamento abaixo usa a matriz UG-ano para contextualizar as UGs cadastradas na UF. "
    "Ele não constitui decomposição direta da métrica territorial quando a referência selecionada "
    "é EXTRATO."
)
if ug_frame.empty:
    st.info("Não há UGs na matriz analítica para a UF e o ano selecionados.")
else:
    chart = ug_frame.head(15).copy()
    chart["SINAL"] = chart["N_TRILHAS_NUCLEO"].gt(0).map(
        {True: "Com sinal", False: "Sem sinal"}
    )
    ug_fig = px.bar(
        chart.sort_values("VALOR_TOTAL"),
        x="VALOR_TOTAL",
        y="CODIGO_UG",
        orientation="h",
        color="SINAL",
        color_discrete_map={"Com sinal": ORANGE, "Sem sinal": BLUE},
        hover_data=["TITULO_UG_SIAFI", "OPERACOES", "N_TRILHAS_NUCLEO"],
        labels={"VALOR_TOTAL": "Compras + saques observáveis", "CODIGO_UG": "UG"},
        title=f"UGs da {selected_uf} · contexto analítico em {year}",
    )
    st.plotly_chart(style_plotly(ug_fig), width="stretch")

    table = ug_frame.copy()
    table["VALOR_COMPRAS_UG"] = table["VALOR_COMPRAS_UG"].map(format_currency)
    table["VALOR_SAQUES_UG"] = table["VALOR_SAQUES_UG"].map(format_currency)
    table["VALOR_TOTAL"] = table["VALOR_TOTAL"].map(format_currency)
    st.dataframe(
        table[
            [
                "CODIGO_UG",
                "TITULO_UG_SIAFI",
                "OPERACOES",
                "VALOR_COMPRAS_UG",
                "VALOR_SAQUES_UG",
                "VALOR_TOTAL",
                "N_TRILHAS_NUCLEO",
                "N_FAMILIAS_NUCLEO",
            ]
        ],
        width="stretch",
        hide_index=True,
    )

with st.expander("Como interpretar o mapa"):
    st.markdown(
        "- **TRANSACAO** usa o ano da data da transação e somente registros com data observável.\n"
        "- **EXTRATO** usa o ano de referência do ciclo do extrato.\n"
        "- As duas referências não são combinadas em um ano híbrido.\n"
        "- `UF_UG` representa a localização cadastral da Unidade Gestora.\n"
        "- Os círculos são âncoras visuais; suas coordenadas não alteram valores, rankings ou sinais.\n"
        "- Sinais analíticos orientam verificação e não constituem conclusão de fraude ou irregularidade."
    )
