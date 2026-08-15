import streamlit as st

from cpgf.ai.tools import tool_catalog
from cpgf.dashboard.components import apply_page_style, page_header
from cpgf.version import KNOWLEDGE_VERSION

st.set_page_config(page_title="Assistente IA · CPGF", page_icon="🤖", layout="wide")
apply_page_style()
page_header(
    "Assistente IA — evidências antes da conversa",
    "A superfície read-only do agente e o contrato do corpus documental já estão estruturados. "
    "Embeddings, RAG semântico e conversa com LLM serão habilitados em etapas posteriores.",
)

left, right = st.columns(2)
with left:
    st.success(
        "Fundação 0.4.0 concluída: contratos estruturados, ferramentas registradas, "
        "roteamento determinístico e guardrails sem chamada a modelo de linguagem."
    )
with right:
    st.success(
        f"Knowledge {KNOWLEDGE_VERSION}: catálogo curado, proveniência, chunking e "
        "recuperação lexical baseline disponíveis sem embeddings."
    )

st.subheader("Ferramentas autorizadas sobre o Serving")
st.dataframe(tool_catalog(), width="stretch", hide_index=True)

st.markdown(
    """
    ### Camadas de evidência preparadas

    - **Serving 1.5.0** — dados e sinais analíticos materializados, somente leitura;
    - **Knowledge 1.0.0** — catálogo documental com natureza, autoridade, política de distribuição,
      hashes e trechos rastreáveis quando a fonte local estiver disponível;
    - **RAG semântico** — ainda não ativo; o retriever lexical serve como baseline determinística;
    - **LLM** — ainda não chamado nesta versão.

    ### Fronteiras preservadas

    - SQL livre não integra o catálogo do agente;
    - nenhuma recomputação, alteração ou recalibração de T01–T09;
    - documentos científicos não são presumidos redistribuíveis por terem sido obtidos pelo projeto;
    - distinção explícita entre **sinal analítico** e **irregularidade confirmada**;
    - estado do agente não armazena credenciais.
    """
)

st.info(
    "Próxima etapa: recuperação semântica/híbrida sobre o Knowledge 1.0.0, preservando "
    "citações e a classificação de autoridade das fontes. A conversa com LLM permanece separada."
)

st.markdown(
    """
    <div class="cpgf-callout">
    O modelo de linguagem será uma camada explicativa. Dados analíticos, documentos e proveniência
    permanecem em contratos independentes e versionados.
    </div>
    """,
    unsafe_allow_html=True,
)
