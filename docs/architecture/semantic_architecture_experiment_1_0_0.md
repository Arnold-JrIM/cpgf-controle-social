# Experimento de Arquitetura Semântica 1.0.0

## Finalidade

Este incremento testa, sobre material já conhecido, se uma camada semântica baseada em LLM pode reduzir as falhas de generalização observadas no Joint Retrieval Holdout 4.0.0 sem transformar o LLM em motor de auditoria ou liberar seu uso na arquitetura de produção.

O diagnóstico contrafactual do JH4 mostrou 18 passes e 30 falhas conjuntas, distribuídas em 13 falhas `router_only`, 2 `planner_only` e 15 `router_and_planner`. A correção perfeita apenas da rota teria teto post-hoc de 31/48 (64,58%). Por isso o experimento precisa distinguir ganho de roteamento e ganho de planejamento.

## Arquiteturas

### A — determinística

Mantém integralmente o fluxo atual:

`pergunta -> Router 1.4 -> Planner 1.3`

Nenhum LLM é chamado.

### B — LLM route-only

O LLM recebe somente a pergunta e escolhe uma rota em vocabulário fechado:

- `knowledge`;
- `methodology`;
- `composite`.

A rota é então entregue ao Planner 1.3, que continua responsável por escopos e temporalidades. Essa arquitetura isola o ganho obtido pela substituição da decisão de roteamento.

### C — híbrida adjudicada

O fluxo determinístico produz primeiro sua proposta de rota, escopos e temporalidades. O LLM recebe a pergunta e essa proposta e devolve, sob schema fechado, uma decisão final de:

- rota;
- escopos;
- temporalidades.

Nesta fase C chama o LLM em todos os casos porque o objetivo é medir separadamente o potencial semântico combinado das duas camadas sem introduzir uma política de detecção de ambiguidade como novo fator de confusão. Se C for selecionada, uma etapa posterior poderá estudar uma política de fallback para reduzir chamadas preservando desempenho.

## Modelo e API

O protocolo congela o alias `gpt-5.6`, três repetições e uso da OpenAI Responses API com Structured Outputs em modo estrito. O experimento não disponibiliza ferramentas ao modelo e usa `store=false`.

O modelo não recebe:

- rota-gabarito;
- escopos-gabarito;
- temporalidades-gabarito;
- documentos-gabarito;
- resultados da medição independente.

## Métricas

A métrica primária é a exatidão conjunta de rota + escopo + temporalidade, calculada por repetição e agregada pela média das três execuções LLM.

Também são registrados:

- exatidão de rota;
- exatidão conjunta dos filtros;
- pior repetição conjunta;
- estabilidade modal das decisões por caso;
- violações de schema;
- quantidade de chamadas ao LLM;
- tokens de entrada e saída;
- latência.

## Regra prospectiva de seleção

B ou C somente pode ser selecionada como candidata para um futuro JH5 se, depois das três repetições:

1. apresentar zero violações de schema;
2. superar A em pelo menos 10 pontos percentuais na métrica conjunta média;
3. apresentar estabilidade modal média de pelo menos 0,90.

Se B e C ficarem a até 2 pontos percentuais uma da outra, B é preferida por possuir menor grau de liberdade: o LLM decide apenas a rota e o Planner permanece determinístico.

Se nenhuma arquitetura cumprir os critérios, nenhuma é selecionada e o JH5 não deve ser usado para resgatar retrospectivamente uma arquitetura insuficiente.

## Independência experimental

O JH4 já é material conhecido. Portanto, qualquer ganho observado neste experimento serve somente para desenvolvimento e seleção arquitetural.

A arquitetura escolhida deverá ser congelada antes de executar um novo Joint Holdout 5.0.0, construído sem consultar o desempenho dessa arquitetura sobre suas perguntas. Somente o JH5 poderá produzir nova evidência de generalização.

## Governança

Este incremento não altera `graph.py`, `router.py` ou `retrieval_planner.py` e não habilita LLM no assistente de produção.

O LLM:

- não executa SQL;
- não acessa Retriever;
- não usa web search ou file search;
- não altera T01–T09;
- não conclui fraude ou irregularidade;
- não produz resposta final ao cidadão.

O workflow de chamadas reais é `workflow_dispatch` e só pode executar na `main`, após o merge do protocolo. Durante o PR, os testes utilizam providers falsos e não fazem chamadas externas.
