# Retrieval Planner 1.0.0

## Objetivo

O Retrieval Planner introduz uma camada determinística entre o roteamento da pergunta e os retrievers do Knowledge. Seu objetivo é inferir, em tempo de execução, o universo documental elegível sem consultar metadados-gabarito do benchmark.

Fluxo-alvo:

`pergunta -> Router -> Retrieval Planner -> Retriever -> evidências`

A conexão com LLM permanece fora do escopo desta versão.

## Problema metodológico

O Retrieval Benchmark 1.0.0 possui `expected_scopes` e `expected_temporal_statuses` para permitir avaliação controlada. Nas avaliações anteriores, o modo `governed` aplicou esses campos diretamente e, por isso, representa um cenário-oráculo útil para isolar a qualidade do retriever.

Em produção, porém, esses campos não existem. O sistema deve inferir os filtros a partir da própria pergunta. O Planner 1.0.0 permite medir essa diferença sem modificar retroativamente o benchmark.

O Retrieval Benchmark 1.0.0 já era conhecido durante o desenvolvimento desta primeira versão do planner. Por isso, a medição `runtime_governed` deste incremento é classificada como **diagnóstico de desenvolvimento/in-sample**. Ela não sustenta, isoladamente, uma alegação de generalização. O código do Planner 1.0.0 é congelado antes da primeira medição e não deve ser ajustado após a observação dos resultados. Um novo holdout, construído após esse congelamento, é requisito para selecionar a política de recuperação de produção.

## Entradas e saídas

Entrada autorizada:

- texto da pergunta;
- decisão determinística do Router, obtida a partir da própria pergunta.

O planner não recebe:

- `gold_document_ids`;
- `supporting_document_ids`;
- `expected_scopes`;
- `expected_temporal_statuses`;
- resultados prévios do benchmark.

Saída `RetrievalPlan`:

- rota do Router;
- `scopes` inferidos;
- `temporal_statuses` inferidos;
- `source_classes` opcionais;
- `trail_hints` diagnósticos;
- justificativa e marcador `deterministic=true`.

## Regras 1.0.0

As regras são intencionalmente pequenas e auditáveis:

- perguntas sobre TCU, acórdãos e fiscalização contínua são direcionadas a `control_external/contextual`;
- Benford, contabilidade forense, Business Intelligence, IA aplicada à auditoria e competência em informação são direcionados a `methodology/contextual`;
- Portal da Transparência combinado com controle social pode usar `cpgf_core` e `methodology`;
- questões gerais, normativas e institucionais do CPGF usam `cpgf_core`;
- literatura/estudos ligados à Lei 14.133 podem admitir `current` e `contextual`;
- perguntas sobre repetição/fracionamento que pedem fontes podem admitir `current` e `contextual`;
- `trail_hints` não são usados para concluir irregularidade nem, nesta versão, para filtrar chunks.

## Modos de avaliação

A Retrieval Evaluation 1.1.0 preserva os resultados anteriores e acrescenta um terceiro cenário:

1. `governed`: usa os filtros-oráculo do benchmark. É mantido como referência controlada/upper bound, não como simulação de produção;
2. `runtime_governed`: usa `PlannedKnowledgeRetriever`, que infere os filtros somente a partir da pergunta;
3. `unfiltered`: não aplica filtros de escopo/temporalidade.

Os três cenários usam o mesmo benchmark, corpus, `k` e retriever subjacente.

## Diagnóstico do planner

Além das métricas de recuperação, a execução registra, somente para avaliação pós-hoc:

- exact match de escopo;
- exact match temporal;
- exact match conjunto;
- precision/recall médios dos filtros inferidos;
- distribuição das rotas;
- detalhe por caso.

Esses campos comparam a saída já produzida pelo planner com o oráculo. O oráculo não participa da geração do plano.

## Congelamento pré-medição

O manifesto `data/manifests/retrieval_planner_1_0_0.json` registra o blob Git do código do planner, os hashes do benchmark e do corpus de referência, a natureza in-sample da primeira avaliação e a proibição de alterar as regras após a primeira medição.

## Governança

- sem LLM;
- sem SQL;
- benchmark 1.0.0 permanece congelado;
- corpus permanece travado ao SHA da baseline lexical;
- embeddings externos continuam opt-in quando semântico/híbrido são avaliados;
- não há escolha de método de produção neste incremento;
- sobreposição entre trilhas ou recuperação documental não confirma fraude, ilegalidade ou fracionamento.
