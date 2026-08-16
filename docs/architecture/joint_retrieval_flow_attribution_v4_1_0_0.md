# Joint Retrieval Flow Attribution — JH4 1.0.0

## Finalidade

Este diagnóstico decompõe post-hoc as falhas da primeira medição independente do Joint Retrieval Holdout 4.0.0 (JH4), realizada antes de qualquer tuning sobre esse conjunto.

O JH4 já é material conhecido. Portanto, esta etapa não produz nova evidência de generalização. Seu objetivo é identificar quais camadas participam das falhas observadas e orientar o próximo experimento arquitetural.

## Medição independente preservada

A primeira medição independente do JH4 registrou:

- 48 casos;
- 18 acertos conjuntos;
- 30 falhas conjuntas;
- 37,50% de exatidão conjunta de rota, escopo e temporalidade.

O benchmark, o Router 1.4.0 e o Retrieval Planner 1.3.0 permanecem congelados nos mesmos hashes da medição independente.

## Contrafactual primário

Para cada pergunta, o diagnóstico primeiro reproduz o fluxo real:

`question -> Router 1.4 -> Planner 1.3`

Em seguida, mantém a pergunta e o oráculo inalterados e substitui somente a decisão de rota pela rota esperada. O Planner 1.3 processa novamente a mesma pergunta sob essa rota contrafactual.

A classificação é:

- `pass`: rota e filtros já estavam corretos;
- `router_only`: a rota real estava errada e a correção da rota torna os filtros exatos;
- `planner_only`: a rota real estava correta, mas os filtros permanecem errados;
- `router_and_planner`: a rota real estava errada e os filtros continuam errados mesmo quando a rota é corrigida para o gabarito.

O sweep por todas as rotas documentais é apenas diagnóstico secundário. A atribuição primária usa a rota esperada.

## Resultados

A decomposição contrafactual congelada é:

- `pass`: 18;
- `router_only`: 13;
- `planner_only`: 2;
- `router_and_planner`: 15.

Entre as 30 falhas conjuntas:

- o Router participa de 28/30 = 93,33%;
- o Planner participa de 17/30 = 56,67%;
- 15/30 = 50% são falhas compartilhadas.

Corrigir post-hoc somente a rota elevaria o resultado conjunto de 18/48 = 37,50% para, no máximo, 31/48 = 64,58% sobre o JH4 conhecido.

Esse valor é um limite diagnóstico, não uma previsão de desempenho de uma futura versão do Router e não uma nova alegação de generalização.

## Padrão por categoria

### Methodology

Dos 12 casos, 5 passam e as 7 falhas são `router_only`. Isso indica que, nessa categoria conhecida, o Planner 1.3 produz os filtros esperados quando recebe a rota correta. A principal limitação está na interpretação semântica inicial.

### Cross-source

Dos 12 casos, apenas 1 passa. Há 2 falhas `router_only` e 9 `router_and_planner`. Portanto, melhorar apenas o roteamento não resolve a maior parte dessa categoria; a interpretação da combinação de fontes precisa chegar também ao planejamento de escopos e temporalidades.

### Control external

Há 5 passes, 2 falhas `planner_only` e 5 `router_and_planner`. Não há casos `router_only`. A camada de planejamento tem participação estrutural nas falhas dessa categoria.

### Normative

Há 7 passes, 4 falhas `router_only` e 1 `router_and_planner`. A rota é o componente dominante entre os erros normativos, mas não é o único.

## Implicação para o experimento com LLM

O diagnóstico sustenta testar um LLM como camada semântica controlada, mas não sustenta substituir toda a arquitetura por uma resposta livre do modelo.

O próximo experimento deve comparar, sobre material já conhecido:

1. **A — determinístico:** Router 1.4 + Planner 1.3;
2. **B — LLM semantic router:** LLM escolhe uma rota dentro de vocabulário fechado e o Planner 1.3 permanece determinístico;
3. **C — híbrido:** Router determinístico decide casos claros e um LLM estruturado atua apenas nos casos ambíguos, podendo produzir rota e plano dentro de contratos fechados.

A análise deve separar pelo menos:

- exatidão de rota;
- exatidão de escopo;
- exatidão temporal;
- critério conjunto;
- desempenho por categoria;
- taxa de acionamento do LLM no híbrido;
- estabilidade entre repetições do LLM;
- violações de schema ou saídas fora do vocabulário permitido.

O LLM não será motor de auditoria, não confirmará irregularidades, não executará SQL arbitrário e não poderá ampliar os escopos ou categorias além do contrato governado.

## Regra para generalização futura

Como o JH4 já é conhecido e passará a ser usado na seleção arquitetural, qualquer conclusão sobre generalização do desenho escolhido deverá ser testada em um **JH5 novo e independente**, congelado antes da primeira execução da arquitetura selecionada.

A avaliação do Retriever e o desbloqueio de qualquer LLM de resposta permanecem posteriores a esse novo gate independente.
