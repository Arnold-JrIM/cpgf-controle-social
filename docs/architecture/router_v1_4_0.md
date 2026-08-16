# Router 1.4.0 — tuning semântico após o Joint Holdout 3.0

## Objetivo

O Router 1.4.0 é um incremento determinístico e isolado de roteamento criado após a primeira medição independente do Joint Retrieval Holdout 3.0 e o diagnóstico contrafactual post-hoc correspondente.

O incremento não constitui nova evidência de generalização. Todas as perguntas usadas para tuning e regressão já eram conhecidas antes da alteração do Router.

## Evidência que motivou o incremento

A primeira medição independente do JH3, com Router 1.3.0 e Retrieval Planner 1.2.0, produziu:

- 31/48 rotas corretas;
- 27/48 casos conjuntos corretos (56,25%).

O diagnóstico post-hoc do PR #47 classificou as 21 falhas conjuntas em:

- 12 `router_only`;
- 4 `planner_only`;
- 5 `router_and_planner`.

O Router participava, portanto, de 17/21 falhas. Quando a rota observada era substituída contrafactualmente pela rota esperada, mantendo o Planner 1.2.0 congelado, 39/48 casos ficavam corretos. Esse valor de 81,25% foi tratado exclusivamente como limite diagnóstico sobre um holdout já conhecido.

## Estratégia do Router 1.4

O Router 1.4 mantém as regras do Router 1.3 como fallback e introduz uma expansão semântica anterior a elas. O tuning foi feito por famílias linguísticas, nunca por identificadores `JH3-*`.

As principais famílias ampliadas foram:

1. **documentação normativa do suprimento** — responsabilidades, combinação normativa, evolução regulatória, contratação direta e limites;
2. **fontes científicas e metodologia** — pesquisa empírica, literatura, análise digital, padrões de dígitos e técnicas forenses;
3. **pontes entre ciência e norma** — perguntas que pedem simultaneamente estudos e fontes normativas/oficiais;
4. **controle externo combinado** — decisões do TCU articuladas com diplomas, regime jurídico ou literatura;
5. **controle social e competência informacional** — dados do CPGF combinados a interpretação, educação informacional e participação social.

Consultas quantitativas continuam fora dessa expansão para que a nova camada não capture solicitações de dados, trilhas, UGs, fornecedores ou análise territorial.

## Correção de sobrealcance durante o tuning

A primeira tentativa do Router 1.4 atingiu 47/48 rotas no JH3, mas transformou uma consulta documental direta a um Acórdão já nomeado em `composite`.

A correção não foi feita por ID. Foi criada uma precedência semântica geral para consultas do tipo “Acórdão X + qual fonte/referência/documento oficial selecionar?”, desde que a pergunta não peça simultaneamente literatura ou enquadramento normativo adicional. Essas consultas permanecem em `knowledge`.

## Resultado em regressões conhecidas

Com Retrieval Planner 1.2.0 congelado no blob `7ee30359cb4457b0bd1a12b43d14f73be410ddaa`, o Router 1.4 obteve:

| Conjunto conhecido | Resultado |
|---|---:|
| Assistant Benchmark | 50/50 |
| Router Holdout 1 | 40/40 |
| Router Holdout 2 | 40/40 |
| Joint Holdout 2 — rota | 40/40 |
| Joint Holdout 3 — rota | 48/48 |
| Joint Holdout 3 — conjunto completo | 39/48 |

No JH3, os nove casos conjuntos ainda divergentes são:

`JH3-003`, `JH3-027`, `JH3-028`, `JH3-029`, `JH3-030`, `JH3-033`, `JH3-034`, `JH3-036` e `JH3-037`.

Todos possuem a rota correta sob o Router 1.4. As divergências remanescentes pertencem à seleção de escopos e/ou temporalidade do Planner 1.2.0.

## Reprodutibilidade

A regressão final foi executada no workflow `31975011818`, head `32bcd07c38185c25c53ad9b0ab6b82e3e01202bd`.

- Python 3.11: job `95233044288`, artifact `9270830957`;
- Python 3.12: job `95233044233`, artifact `9270826492`;
- os JSONs são idênticos byte a byte;
- SHA-256 do JSON: `688827de31264b4e18efcc73a16b15761ed88b9cae80efc7a8890988e820fe39`;
- blob final do Router: `89150b97e9c87d9af0d0b0f888870dcc74ef86b1`.

## Governança

O JH3 é material conhecido desde a primeira medição do PR #46. Por isso, 48/48 de rotas e 39/48 no fluxo conjunto são resultados de regressão pós-tuning e não podem ser apresentados como acurácia independente futura.

O incremento:

- não altera `retrieval_planner.py`;
- mantém o Planner 1.2.0 pelo mesmo blob da medição independente;
- não executa Retriever, LLM, SQL ou embeddings externos;
- preserva os manifests das medições independentes e diagnósticos anteriores;
- não sustenta prontidão de produção;
- não desbloqueia o LLM.

## Próxima sequência

A próxima camada de tuning deve ser o **Retrieval Planner 1.3.0**, com Router 1.4.0 congelado. O JH3 será usado apenas como regressão conhecida para os nove casos remanescentes.

Após esse incremento, qualquer nova alegação de generalização exige um **Joint Holdout 4.0 independente**, criado, validado e congelado antes da primeira execução do novo par Router + Planner.
