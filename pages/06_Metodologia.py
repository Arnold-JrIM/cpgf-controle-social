import streamlit as st

from cpgf.dashboard.components import apply_page_style, page_header, render_disclaimer
from cpgf.dashboard.data import TRAIL_LABELS
from cpgf.version import (
    GEO_VERSION,
    MOTOR_VERSION,
    PREPARATION_VERSION,
    RULES_VERSION,
    SERVING_VERSION,
)

st.set_page_config(page_title="Metodologia · CPGF", page_icon="📚", layout="wide")
apply_page_style()
page_header(
    "Metodologia e rastreabilidade",
    "A aplicação separa preparação, regras analíticas, governança estatística e serving. "
    "Essa arquitetura permite reproduzir os resultados sem recalculá-los no navegador.",
)
render_disclaimer()

c1, c2, c3, c4 = st.columns(4)
c1.metric("Preparação", PREPARATION_VERSION)
c2.metric("Regras", RULES_VERSION)
c3.metric("Motor/Governança", MOTOR_VERSION)
c4.metric("Serving", SERVING_VERSION)

st.markdown(
    f"""
    ### Cadeia de processamento

    **Dados públicos → Preparação {PREPARATION_VERSION} → T01–T09 {RULES_VERSION}
    → Governança {MOTOR_VERSION} → Serving {SERVING_VERSION} → Streamlit**

    O dashboard consulta apenas o bundle materializado e validado em DuckDB read-only.
    A dimensão geográfica permanece versionada como **{GEO_VERSION}**, mas ainda não está
    materializada no Serving 1.4.0; por isso, o painel não infere UF ou município.
    """
)

st.subheader("Trilhas analíticas")
for code, name in TRAIL_LABELS.items():
    st.markdown(f"- **{code}** — {name}")

st.subheader("Governança estatística")
st.markdown(
    """
    O Motor 1.3.2 analisa sobreposição (Jaccard e Phi), contribuição marginal,
    elegibilidade estatística, VIF, índices de condição e PCA. Os diagnósticos são
    descritivos e não autorizam remoção automática de trilhas. T08 e T09 são tratados
    como contexto no núcleo multivariado.
    """
)

st.subheader("Cobertura temporal")
st.markdown(
    """
    O snapshot canônico cobre **janeiro de 2013 a julho de 2026**. Para diagnósticos
    estatísticos comparáveis, os exercícios completos de **2013 a 2025** formam o
    universo principal. O ano de 2026 permanece disponível nas matrizes com status
    explícito de período parcial.
    """
)
