import streamlit as st

from cpgf.ai.tools import tool_catalog
from cpgf.dashboard.components import apply_page_style, page_header
from cpgf.version import KNOWLEDGE_VERSION

st.set_page_config(page_title="Assistente IA · CPGF", page_icon="🤖", layout="wide")
apply_page_style()
page_header(
    "Assistente IA — evidências antes da conversa",
    "A superfície read-only do agente e o corpus documental governado já estão estruturados. "
    "Embeddings, RAG semântico e conversa com LLM serão habilitados em etapas posteriores.",
)

left, right = st.columns(2)
with left:
    st.success(
        "Fundação do agente concluída: contratos estruturados, ferramentas registradas, "
        "roteamento determinístico e guardrails sem chamada a modelo de linguagem."
    )
with right:
    st.success(
        f"Knowledge {KNOWLEDGE_VERSION}: 45 referências catalogadas, 35 elegíveis para recuperação padrão, "
        "com escopo, temporalidade, autoridade e proveniência explícitos."
    )

st.subheader("Ferramentas autorizadas sobre o Serving")
st.dataframe(tool_catalog(), width="stretch", hide_index=True)

st.markdown(
    """
    ### Camadas de evidência preparadas

    - **Serving 1.5.0** — dados e sinais analíticos materializados, somente leitura;
    - **Knowledge 1.1.0** — corpus governado em seis escopos: núcleo CPGF, controle externo,
      metodologia, histórico, institucional MB e descoberta;
    - **recuperação lexical** — baseline determinística, por padrão exclui fontes históricas,
      institucionais específicas e materiais apenas de descoberta;
    - **RAG semântico** — ainda não ativo;
    - **LLM** — ainda não chamado nesta versão.

    ### Governança documental

    - PDFs originais permanecem fora do Git; o catálogo registra caminho esperado, hash, tamanho e páginas;
    - `supports_trails` distingue fundamento direto de `related_trails`, que representa pertinência contextual;
    - fontes históricas exigem opt-in e não orientam automaticamente respostas sobre vigência atual;
    - decisões do TCU formam uma classe própria de evidência de controle externo;
    - a Macrofunção SIAFI 02.11.21 está catalogada e validada por arquivo, mas fica fora da recuperação padrão
      enquanto a cópia local não oferecer texto extraível de forma confiável;
    - documentos científicos não são presumidos redistribuíveis apenas por terem sido obtidos legalmente.
    """
)

st.info(
    "Próxima etapa: comparar a baseline lexical do Knowledge 1.1.0 com recuperação semântica/híbrida, "
    "preservando citações, escopo, temporalidade e autoridade. A conversa com LLM permanece separada."
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
