import streamlit as st

from cpgf.dashboard.components import apply_page_style, page_header

st.set_page_config(page_title="Assistente IA · CPGF", page_icon="🤖", layout="wide")
apply_page_style()
page_header(
    "Assistente IA",
    "Espaço reservado ao assistente conversacional que explicará dados públicos, trilhas "
    "e normas sem alterar o motor analítico.",
)

st.info(
    "A integração do assistente será feita em etapa própria. O dashboard já está preparado "
    "para fornecer ao agente apenas consultas read-only sobre views autorizadas."
)

st.markdown(
    """
    ### Guardrails previstos

    - respostas fundamentadas em dados materializados e fontes normativas;
    - consultas somente de leitura;
    - nenhuma recomputação ou alteração de T01–T09 pelo modelo de linguagem;
    - distinção explícita entre **sinal analítico** e **irregularidade confirmada**;
    - rastreabilidade das fontes utilizadas na resposta;
    - modo de demonstração e opção BYOK com chave mantida apenas na sessão.
    """
)

st.markdown(
    """
    <div class="cpgf-callout">
    O modelo de linguagem será uma camada explicativa. A lógica de auditoria permanece
    determinística e versionada fora do LLM.
    </div>
    """,
    unsafe_allow_html=True,
)
