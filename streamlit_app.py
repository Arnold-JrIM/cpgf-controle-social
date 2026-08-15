import streamlit as st

from cpgf.dashboard.data import serving_health
from cpgf.version import (
    APP_VERSION,
    GEO_VERSION,
    MOTOR_VERSION,
    RULES_VERSION,
    SERVING_VERSION,
)

st.set_page_config(
    page_title="CPGF — Controle Social",
    page_icon="💳",
    layout="wide",
)
st.title("💳 CPGF — Controle Social Orientado por Dados e IA")
st.caption(
    f"Aplicação {APP_VERSION} · Regras {RULES_VERSION} · "
    f"Motor {MOTOR_VERSION} · Serving {SERVING_VERSION} · Geo {GEO_VERSION}"
)

health = serving_health()
if health["status"] == "READY":
    st.success(
        "Camada analítica materializada disponível. "
        "A aplicação consulta o Serving em modo read-only e não recalcula o motor."
    )
else:
    st.warning(
        "A camada de Serving ainda não está disponível neste ambiente. "
        "A aplicação permanece inicializável, mas as páginas analíticas ficarão "
        f"sem dados até o bootstrap ser concluído. Detalhe: {health['message']}"
    )

col1, col2, col3, col4 = st.columns(4)
col1.metric("Regras", RULES_VERSION)
col2.metric("Motor/Governança", MOTOR_VERSION)
col3.metric("Serving", SERVING_VERSION)
col4.metric("Tabelas disponíveis", int(health.get("tables", 0)))

st.markdown(
    """
### Princípio de uso
As saídas do projeto são **sinais, indicadores e condições para verificação**.
Não constituem conclusões automáticas de fraude, irregularidade ou fracionamento.
"""
)
