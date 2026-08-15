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
    ### Camadas de evidência e avaliação preparadas

    - **Serving 1.5.0** — dados e sinais analíticos materializados, somente leitura;
    - **Knowledge {KNOWLEDGE_VERSION}** — corpus governado para conceitos, normas e literatura;
    - **Router {ROUTER_VERSION}** — distingue a intenção da pergunta das camadas de evidência necessárias;
    - **`knowledge`** — rota para perguntas conceituais e normativas;
    - **`composite`** — rota reservada a perguntas que exigem combinar mais de uma camada, como dado analítico
      e interpretação metodológica ou normativa;
    - **Benchmark {BENCHMARK_VERSION}** — 50 perguntas usadas como referência de desenvolvimento;
    - **Router Holdout {ROUTER_HOLDOUT_VERSION}** — 40 perguntas congeladas antes da primeira medição do
      Router 1.0.0, sem repetição exata das perguntas do benchmark de desenvolvimento;
    - **LLM** — ainda não chamado nesta versão.

    ### Desenvolvimento × generalização observada

    - a baseline anterior ao Router 1.0.0 era de 22/50 rotas exatas (**44%**);
    - após o ajuste, o Router 1.0.0 direcionou corretamente 50/50 casos do benchmark de desenvolvimento
      (**100% in-sample**);
    - no holdout interno não usado naquele ajuste, o mesmo Router 1.0.0 acertou 19/40 rotas (**47,5%**);
    - `trails` e `suppliers` tiveram 100% no holdout e `knowledge`, 87,5%; por outro lado,
      `methodology` ficou em 16,7%, `overview` e `composite` em 25%, e `territorial`/`ugs` em 0%;
    - a diferença revela fragilidade de generalização das regras atuais, sobretudo dependência de formas
      lexicais específicas e da precedência entre classificadores;
    - o holdout é interno ao projeto e não representa estimativa de acurácia de produção nem validação externa.

    ### Governança do roteamento e da evidência

    - o Router 1.0.0 não foi alterado depois de observados os erros do holdout neste incremento;
    - este holdout poderá servir como regressão de versões futuras, mas deixará de ser conjunto não visto se
      seus erros forem usados para ajustar o roteador;
    - uma versão futura ajustada com base nesses erros deverá ser avaliada em **novo conjunto não visto**;
    - rota e fonte de evidência são contratos diferentes: uma explicação de T01–T09 pode permanecer
      `methodology` e ainda exigir apoio do Knowledge;
    - consultas quantitativas permanecem vinculadas ao Serving, sem SQL livre;
    - perguntas conceituais/normativas usam Knowledge e não recomputam sinais analíticos;
    - perguntas compostas não autorizam conclusões categóricas: sinais continuam sendo triagem, não confirmação
      automática de irregularidade;
    - nenhuma rota executa ferramenta ou chama LLM automaticamente nesta versão.
    """
)

st.info(
    "Próxima etapa: evoluir o Router para uma versão posterior usando o holdout 1.0.0 apenas como diagnóstico "
    "e regressão; a nova versão deverá ser validada em outro conjunto não visto. Em paralelo, permanece prevista "
    "a avaliação lexical, semântica e híbrida no corpus local real."
)

st.markdown(
    """
    <div class="cpgf-callout">
    O modelo de linguagem será uma camada explicativa. Dados analíticos, documentos, índice vetorial,
    roteamento, benchmark, holdout e proveniência permanecem em contratos independentes e versionados.
    </div>
    """,
    unsafe_allow_html=True,
)
