import streamlit as st

from cpgf.ai.tools import tool_catalog
from cpgf.dashboard.components import apply_page_style, page_header
from cpgf.version import BENCHMARK_VERSION, KNOWLEDGE_VERSION, ROUTER_VERSION

st.set_page_config(page_title="Assistente IA · CPGF", page_icon="🤖", layout="wide")
apply_page_style()
page_header(
    "Assistente IA — evidências antes da conversa",
    "A superfície read-only do agente, o corpus documental governado, os mecanismos de recuperação, "
    "o roteador e um benchmark de referência estão estruturados. A conversa com LLM permanece desabilitada.",
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
    - **Benchmark {BENCHMARK_VERSION}** — 50 perguntas governadas cobrindo conceitos/normas, consultas ao
      Serving, consultas de trilhas, explicação de T01–T09 e interpretação segura;
    - **LLM** — ainda não chamado nesta versão.

    ### Resultado de desenvolvimento do roteador

    - a baseline anterior ao Router 1.0.0 era de 22/50 rotas exatas (**44%**);
    - o Router 1.0.0 direcionou corretamente os 50/50 casos do benchmark congelado (**100% in-sample**);
    - esse resultado **não representa acurácia de produção nem generalização para perguntas novas**: o benchmark
      foi usado como gate de desenvolvimento e deve ser complementado por conjunto externo/holdout e avaliação
      de paráfrases não utilizadas no ajuste;
    - testes unitários adicionais verificam paráfrases fora dos 50 casos e preservam perguntas fora do domínio
      como `unsupported`.

    ### Governança do roteamento e da evidência

    - rota e fonte de evidência são contratos diferentes: uma explicação de T01–T09 pode permanecer
      `methodology` e ainda exigir apoio do Knowledge;
    - consultas quantitativas permanecem vinculadas ao Serving, sem SQL livre;
    - perguntas conceituais/normativas usam Knowledge e não recomputam sinais analíticos;
    - perguntas compostas não autorizam conclusões categóricas: sinais continuam sendo triagem, não confirmação
      automática de irregularidade;
    - nenhuma rota executa ferramenta ou chama LLM automaticamente nesta versão;
    - perguntas sensíveis à vigência permanecem marcadas no benchmark para futura verificação web controlada.
    """
)

st.info(
    "Próxima etapa: validar generalização do roteamento em um conjunto externo e usar o Benchmark 1.0.0 "
    "para avaliar a recuperação lexical, semântica e híbrida no corpus local real. O LLM continua separado."
)

st.markdown(
    """
    <div class="cpgf-callout">
    O modelo de linguagem será uma camada explicativa. Dados analíticos, documentos, índice vetorial,
    roteamento, benchmark e proveniência permanecem em contratos independentes e versionados.
    </div>
    """,
    unsafe_allow_html=True,
)
