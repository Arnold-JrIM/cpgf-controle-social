import streamlit as st

from cpgf.ai.tools import tool_catalog
from cpgf.dashboard.components import apply_page_style, page_header
from cpgf.version import (
    BENCHMARK_VERSION,
    KNOWLEDGE_VERSION,
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
    - **`knowledge`** — rota para perguntas conceituais e normativas;
    - **`composite`** — rota para perguntas que exigem combinar camadas, sem autorizar conclusão categórica;
    - **Benchmark {BENCHMARK_VERSION}** — 50 perguntas usadas como referência de desenvolvimento;
    - **Router Holdout {ROUTER_HOLDOUT_VERSION}** — 40 perguntas originalmente congeladas antes da primeira
      medição do Router 1.0.0;
    - **LLM** — ainda não chamado nesta versão.

    ### O que aprendemos com o Router 1.0.0

    - antes do Router 1.0.0, a baseline era de 22/50 rotas exatas (**44%**);
    - o Router 1.0.0 alcançou 50/50 no benchmark de desenvolvimento (**100% in-sample**);
    - na primeira aplicação ao holdout então não visto, o Router 1.0.0 obteve 19/40 (**47,5%**);
    - o resultado revelou dependência excessiva de formulações lexicais específicas, principalmente nas rotas
      `methodology`, `overview`, `territorial`, `ugs` e `composite`.

    ### Router {ROUTER_VERSION}: regressão conhecida, não nova generalização

    - o Router 1.1.0 foi ajustado usando os padrões de erro observados após aquela primeira medição;
    - por isso, o Router Holdout {ROUTER_HOLDOUT_VERSION} deixou de ser conjunto não visto para esta versão;
    - no benchmark de desenvolvimento, o Router 1.1.0 preserva 50/50 rotas exatas;
    - no conjunto de regressão conhecido de 40 perguntas, o Router 1.1.0 alcança 40/40;
    - **esse 40/40 não estima generalização nem acurácia de produção**: apenas verifica que os padrões conhecidos
      foram incorporados sem quebrar o contrato anterior;
    - uma avaliação fora da amostra do Router 1.1.0 exige um **novo holdout congelado antes da medição**.

    ### Governança do roteamento e da evidência

    - as 50 perguntas do benchmark e as 40 perguntas do holdout 1.0.0 permanecem imutáveis;
    - consultas quantitativas permanecem vinculadas ao Serving e não habilitam SQL livre;
    - perguntas conceituais/normativas usam Knowledge sem recomputar sinais analíticos;
    - explicações de T01–T09 podem combinar metodologia e Knowledge, mas os sinais continuam sendo triagem;
    - divergência de Benford, proximidade de limite, concentração, repetição ou compra em fim de semana não
      constituem, isoladamente, confirmação automática de fraude ou irregularidade;
    - nenhuma rota executa ferramenta ou chama LLM automaticamente nesta versão.
    """
)

st.info(
    "Próxima etapa: congelar um novo conjunto não visto e medir o Router 1.1.0 sem novos ajustes. "
    "Só depois dessa medição o novo conjunto poderá ser usado para diagnóstico. A avaliação lexical, "
    "semântica e híbrida do Knowledge permanece uma etapa independente."
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
