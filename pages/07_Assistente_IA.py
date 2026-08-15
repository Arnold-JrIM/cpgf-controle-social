import streamlit as st

from cpgf.ai.tools import tool_catalog
from cpgf.dashboard.components import apply_page_style, page_header
from cpgf.version import KNOWLEDGE_VERSION

st.set_page_config(page_title="Assistente IA · CPGF", page_icon="🤖", layout="wide")
apply_page_style()
page_header(
    "Assistente IA — evidências antes da conversa",
    "A superfície read-only do agente, o corpus documental governado e os mecanismos de recuperação "
    "lexical, semântica e híbrida estão estruturados. A conversa com LLM permanece desabilitada.",
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
    - **Knowledge 1.2.0** — corpus governado em seis escopos: núcleo CPGF, controle externo,
      metodologia, histórico, institucional MB e descoberta;
    - **recuperação lexical** — baseline determinística preservada;
    - **recuperação semântica** — implementada por similaridade cosseno sobre índice vetorial local;
    - **recuperação híbrida** — fusão por Reciprocal Rank Fusion (RRF), evitando comparar diretamente
      escalas de score lexical e vetorial;
    - **LLM** — ainda não chamado nesta versão.

    ### Governança documental e do índice

    - PDFs originais permanecem fora do Git; o catálogo registra caminho esperado, hash, tamanho e páginas;
    - `supports_trails` distingue fundamento direto de `related_trails`, que representa pertinência contextual;
    - filtros de escopo, temporalidade e `retrieval_default` continuam valendo também para a busca semântica;
    - fontes históricas exigem opt-in e não orientam automaticamente respostas sobre vigência atual;
    - o índice vetorial é artefato local reproduzível e não é versionado no Git;
    - a construção real do índice exige credencial explícita do provedor de embeddings e não ocorre no CI padrão;
    - a Macrofunção SIAFI 02.11.21 permanece fora da recuperação enquanto a cópia local não oferecer texto
      extraível de forma confiável;
    - documentos científicos não são presumidos redistribuíveis apenas por terem sido obtidos legalmente.
    """
)

st.info(
    "Próxima etapa: executar e avaliar o índice semântico sobre o corpus local real, comparando lexical, "
    "semântico e híbrido em um conjunto de consultas de referência. A conversa com LLM continua separada."
)

st.markdown(
    """
    <div class="cpgf-callout">
    O modelo de linguagem será uma camada explicativa. Dados analíticos, documentos, índice vetorial e
    proveniência permanecem em contratos independentes e versionados.
    </div>
    """,
    unsafe_allow_html=True,
)
