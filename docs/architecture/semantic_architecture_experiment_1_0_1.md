# Experimento de Arquitetura Semântica 1.0.1

## Emenda pré-experimental

A versão 1.0.1 substitui exclusivamente o modelo previsto na versão 1.0.0 antes da primeira execução real do LLM.

- modelo anterior: `gpt-5.6`;
- modelo congelado nesta versão: `gpt-4o-mini-2024-07-18`;
- execuções `workflow_dispatch` observadas antes da emenda: **0**;
- benchmark, prompts semânticos, arquiteturas A/B/C, três repetições, métricas e regra prospectiva de seleção permanecem inalterados.

A escolha usa um snapshot fixo do GPT-4o mini para reduzir custo e melhorar reprodutibilidade. A tarefa experimental é deliberadamente estreita: classificação de rota e adjudicação estruturada de filtros, sem resposta ao mérito, Retriever ou ferramentas externas.

## Finalidade

O experimento testa, sobre o JH4 já conhecido, se uma camada semântica baseada em LLM pode reduzir as falhas observadas no fluxo determinístico sem transformar o LLM em motor de auditoria ou liberar seu uso na arquitetura de produção.

O diagnóstico contrafactual do JH4 mostrou 18 passes e 30 falhas conjuntas, distribuídas em 13 `router_only`, 2 `planner_only` e 15 `router_and_planner`. A correção perfeita apenas da rota teria teto post-hoc de 31/48 (64,58%).

## Arquiteturas

### A — determinística

`pergunta -> Router 1.4 -> Planner 1.3`

### B — LLM route-only

O LLM recebe somente a pergunta e escolhe uma rota no vocabulário fechado `knowledge`, `methodology` ou `composite`. O Planner 1.3 continua responsável por escopos e temporalidades.

### C — híbrida adjudicada

O fluxo determinístico produz uma proposta. O LLM recebe pergunta + proposta e devolve, sob schema fechado, rota, escopos e temporalidades. Nesta fase, C chama o LLM em todos os casos para medir o potencial combinado sem introduzir uma política de detecção de ambiguidade como fator adicional.

## Modelo e API

O protocolo congela `gpt-4o-mini-2024-07-18`, três repetições e OpenAI Responses API com Structured Outputs estrito. O experimento usa `store=false` e não disponibiliza ferramentas ao modelo.

O modelo não recebe rota-gabarito, escopos-gabarito, temporalidades-gabarito, documentos-gabarito nem resultados da medição independente.

## Métricas e seleção

A métrica primária é a exatidão conjunta de rota + escopo + temporalidade. Também são registrados exatidão de rota, filtros conjuntos, pior repetição, estabilidade modal, violações de schema, chamadas ao LLM, tokens e latência.

B ou C somente pode ser candidata ao futuro JH5 se:

1. apresentar zero violações de schema;
2. superar A em pelo menos 10 pontos percentuais na métrica conjunta média;
3. apresentar estabilidade modal média de pelo menos 0,90.

Empate até 2 pontos percentuais favorece B por possuir menor grau de liberdade. Se nenhuma arquitetura cumprir os critérios, nenhuma será selecionada.

## Independência e governança

O JH4 é material conhecido e serve apenas para desenvolvimento/seleção. Qualquer arquitetura escolhida deverá ser congelada antes de um JH5 novo e independente.

O incremento não altera `graph.py`, `router.py`, `retrieval_planner.py`, T01–T09 ou o benchmark JH4. O LLM não executa SQL, Retriever, web search ou file search e não produz resposta final ao cidadão.

## Referência arquitetural complementar

A análise do repositório `devfullcycle/techweekia9-multi-agents-rag` foi registrada separadamente em `docs/architecture/multi_agent_rag_reference_notes.md`. Os insights são tratados como referência para etapas futuras de retrieval e síntese; eles não alteram o experimento A/B/C antes de sua primeira execução real.