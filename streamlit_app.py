import streamlit as st

from cpgf.version import APP_VERSION, GEO_VERSION, MOTOR_VERSION, RULES_VERSION


st.set_page_config(
    page_title="CPGF — Controle Social",
    page_icon="💳",
    layout="wide",
)
st.title("💳 CPGF — Controle Social Orientado por Dados e IA")
st.caption(
    f"Aplicação {APP_VERSION} · Regras {RULES_VERSION} · "
    f"Motor {MOTOR_VERSION} · Geo {GEO_VERSION}"
)
st.info(
    "Esqueleto inicial da aplicação de produção. "
    "As regras analíticas ainda não foram portadas para src/."
)

col1, col2, col3 = st.columns(3)
col1.metric("Regras", RULES_VERSION)
col2.metric("Motor/Governança", MOTOR_VERSION)
col3.metric("Geo", GEO_VERSION)

st.markdown(
    """
### Princípio de uso
As saídas do projeto são **sinais, indicadores e condições para verificação**.
Não constituem conclusões automáticas de fraude, irregularidade ou fracionamento.
"""
)
