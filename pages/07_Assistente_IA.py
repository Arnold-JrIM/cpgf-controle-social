import streamlit as st

from cpgf.ai.tools import tool_catalog
from cpgf.dashboard.components import apply_page_style, page_header
from cpgf.version import BENCHMARK_VERSION, KNOWLEDGE_VERSION

st.set_page_config(page_title="Assistente IA · CPGF", page_icon="🤖", layout="wide")
apply_page_style()
page_header(
    "Assistente IA — evidências antes da conversa",
    "A superfície read-only do agente, o corpus documental governado, os mecanismos de recuperação "
    "e um benchmark de roteamento/recuperação estão estruturados. A conversa com LLM permanece desabilitada.",
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
    f"""
    ### Camadas de evidência e avaliação preparadas

    - **Serving 1.5.0** — dados e sinais analíticos materializados, somente leitura;
    - **Knowledge 1.2.0** — corpus governado em seis escopos: núcleo CPGF, controle externo,
      metodologia, histórico, institucional MB e descoberta;
    - **recuperação lexical** — baseline determinística preservada;
    - **recuperação semântica** — implementada por similaridade cosseno sobre índice vetorial local;
    - **recuperação híbrida** — fusão por Reciprocal Rank Fusion (RRF), evitando comparar diretamente
      escalas de score lexical e vetorial;
    - **Benchmark {BENCHMARK_VERSION}** — 50 perguntas governadas cobrindo conceitos/normas, consultas ao
      Serving, consultas de trilhas, explicação de T01–T09 e interpretação segura;
    - **LLM** — ainda não chamado nesta versão.

    ### Baseline do roteador atual

    - 22 de 50 perguntas foram direcionadas exatamente à rota-alvo (**44%**);
    - entre os 29 casos cuja rota-alvo já existe no roteador atual, houve 22 acertos (**75,86%**);
    - as rotas `knowledge` e `composite` permanecem deliberadamente ausentes do roteador atual e aparecem
      no benchmark como lacunas a serem tratadas em evolução posterior, sem alterar retroativamente a baseline.

    ### Governança documental, do índice e da avaliação

    - PDFs originais permanecem fora do Git; o catálogo registra caminho esperado, hash, tamanho e páginas;
    - `supports_trails` distingue fundamento direto de `related_trails`, que representa pertinência contextual;
    - filtros de escopo, temporalidade e `retrieval_default` continuam valendo também para a busca semântica;
    - fontes históricas exigem opt-in e não orientam automaticamente respostas sobre vigência atual;
    - o índice vetorial é artefato local reproduzível e não é versionado no Git;
    - a construção real do índice exige credencial explícita do provedor de embeddings e não ocorre no CI padrão;
    - perguntas sensíveis à vigência são marcadas no benchmark para futura verificação por busca web controlada;
    - sinais analíticos continuam sendo tratados como triagem e não como confirmação automática de irregularidade.
    """
)

st.info(
    "Próxima etapa: usar o Benchmark 1.0.0 para comparar lexical, semântico e híbrido no corpus local real e, "
    "depois, aprimorar o roteamento de forma mensurável. A conversa com LLM continua separada."
)

st.markdown(
    """
    <div class="cpgf-callout">
    O modelo de linguagem será uma camada explicativa. Dados analíticos, documentos, índice vetorial,
    benchmark e proveniência permanecem em contratos independentes e versionados.
    </div>
    """,
    unsafe_allow_html=True,
)
