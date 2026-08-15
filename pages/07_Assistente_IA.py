import streamlit as st

from cpgf.ai.tools import tool_catalog
from cpgf.dashboard.components import apply_page_style, page_header

st.set_page_config(page_title="Assistente IA · CPGF", page_icon="🤖", layout="wide")
apply_page_style()
page_header(
    "Assistente IA — fundação segura",
    "A superfície read-only do agente já está implementada. A conversa com LLM e o RAG "
    "normativo serão ativados em etapas posteriores, sem alterar o motor analítico.",
)

st.success(
    "Fundação 0.4.0-dev ativa: contratos estruturados, roteamento determinístico, "
    "ferramentas registradas e guardrails podem ser testados sem chamar um modelo de linguagem."
)

st.subheader("Ferramentas autorizadas")
st.dataframe(tool_catalog(), width="stretch", hide_index=True)

st.markdown(
    """
    ### Fronteiras já aplicadas

    - consultas somente por ferramentas registradas sobre views materializadas;
    - SQL livre não integra o catálogo do agente;
    - nenhuma recomputação, alteração ou recalibração de T01–T09;
    - contratos Pydantic rejeitam argumentos extras e parâmetros fora do domínio;
    - distinção explícita entre **sinal analítico** e **irregularidade confirmada**;
    - estado do agente não armazena credenciais;
    - nenhuma chamada a LLM é realizada nesta versão.
    """
)

st.info(
    "Próxima etapa: RAG normativo com fontes rastreáveis. Somente depois será habilitada a "
    "camada conversacional e a opção BYOK com chave mantida apenas na sessão."
)

st.markdown(
    """
    <div class="cpgf-callout">
    O modelo de linguagem será uma camada explicativa. A lógica de auditoria permanece
    determinística, versionada e independente do LLM.
    </div>
    """,
    unsafe_allow_html=True,
)
