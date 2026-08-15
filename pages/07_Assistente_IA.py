import streamlit as st

from cpgf.ai.tools import tool_catalog
from cpgf.dashboard.components import apply_page_style, page_header
from cpgf.version import (
    BENCHMARK_VERSION,
    KNOWLEDGE_VERSION,
    ROUTER_HOLDOUT_V2_VERSION,
    ROUTER_HOLDOUT_VERSION,
    ROUTER_VERSION,
)

st.set_page_config(page_title="Assistente IA · CPGF", page_icon="🤖", layout="wide")
apply_page_style()
page_header(
    "Assistente IA — evidências antes da conversa",
    "A superfície read-only do agente, o corpus documental governado, os mecanismos de recuperação, "
    "o roteador e conjuntos separados de desenvolvimento e avaliação estão estruturados. "
    "A conversa com LLM permanece desabilitada.",
)

left, right = st.columns(2)
with left:
    st.success(
        f"Router {ROUTER_VERSION}: roteamento determinístico com plano explícito de camadas de evidência, "
        "sem chamada a modelo de linguagem e sem execução automática de ferramentas."
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
    ### Camadas de evidência e conjuntos de avaliação

    - **Serving 1.5.0** — dados e sinais analíticos materializados, somente leitura;
    - **Knowledge {KNOWLEDGE_VERSION}** — corpus governado para conceitos, normas e literatura;
    - **Router {ROUTER_VERSION}** — distingue intenção da pergunta e camadas de evidência necessárias;
    - **Benchmark {BENCHMARK_VERSION}** — 50 perguntas de desenvolvimento;
    - **Router Holdout {ROUTER_HOLDOUT_VERSION}** — 40 perguntas usadas para a primeira avaliação do Router 1.0.0
      e depois convertidas em regressão conhecida do Router 1.1.0;
    - **Router Holdout {ROUTER_HOLDOUT_V2_VERSION}** — 40 novas perguntas congeladas antes da primeira medição
      válida do Router 1.1.0;
    - **LLM** — ainda não chamado nesta versão.

    ### Evidência de generalização do roteamento

    - o Router 1.0.0 obteve 19/40 (**47,5%**) no Holdout 1.0.0 quando esse conjunto ainda não havia sido usado
      para ajuste;
    - o Router 1.1.0 preservou 50/50 no benchmark de desenvolvimento e 40/40 no antigo conjunto de regressão;
    - no novo Holdout 2.0.0, não usado no ajuste do Router 1.1.0, foram observadas 23/40 rotas exatas
      (**57,5%**);
    - `knowledge`, `trails`, `ugs` e `suppliers` atingiram 100% neste conjunto; `territorial`, 50%;
      `overview` e `methodology`, 25%; e `composite`, 0%;
    - a diferença entre 47,5% e 57,5% é favorável, mas os dois holdouts contêm perguntas diferentes e não formam
      uma comparação pareada nem estimativa formal de ganho de acurácia;
    - os 17 erros do Holdout 2.0.0 permanecem intocados neste incremento.

    ### Governança do roteamento e da evidência

    - o Holdout 2.0.0 válido foi congelado antes da primeira execução que alcançou o roteamento;
    - uma tentativa anterior falhou na validação do esquema antes de qualquer caso ser roteado e não é tratada
      como medição;
    - consultas quantitativas permanecem vinculadas ao Serving e não habilitam SQL livre;
    - perguntas conceituais/normativas usam Knowledge sem recomputar sinais analíticos;
    - explicações de T01–T09 podem combinar metodologia e Knowledge, mas os sinais continuam sendo triagem;
    - divergência de Benford, proximidade de limite, concentração, repetição ou compra em fim de semana não
      constituem, isoladamente, confirmação automática de fraude ou irregularidade;
    - nenhuma rota executa ferramenta ou chama LLM automaticamente nesta versão.
    """
)

st.info(
    "Próxima etapa de roteamento: usar os erros do Holdout 2.0.0 apenas em uma versão posterior; a partir desse "
    "momento, ele passará a ser regressão conhecida e uma nova alegação de generalização exigirá outro conjunto. "
    "Em paralelo, a avaliação lexical, semântica e híbrida do Knowledge permanece independente."
)

st.markdown(
    """
    <div class="cpgf-callout">
    O modelo de linguagem será uma camada explicativa. Dados analíticos, documentos, índice vetorial,
    roteamento, benchmark, holdouts e proveniência permanecem em contratos independentes e versionados.
    </div>
    """,
    unsafe_allow_html=True,
)
