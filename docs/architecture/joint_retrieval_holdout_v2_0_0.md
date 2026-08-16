# Joint Retrieval Holdout 2.0.0

## Finalidade

O Joint Retrieval Holdout 2.0.0 é o primeiro conjunto criado **depois** do congelamento conjunto do Router 1.2.0 e do Retrieval Planner 1.1.0. Seu objetivo é produzir nova evidência de generalização do fluxo documental, sem reutilizar o conjunto que orientou o tuning dessas versões.

A unidade principal de avaliação deixa de ser apenas o filtro produzido pelo Planner. Cada pergunta contém três componentes independentes do oráculo:

1. `expected_route` — intenção documental que o Router deve selecionar;
2. `expected_scopes` — universos documentais que o Planner deve habilitar;
3. `expected_temporal_statuses` — combinação de fontes correntes e/ou contextuais.

A métrica principal da primeira medição será a concordância exata conjunta desses três elementos.

## Freeze antes da medição

O benchmark foi criado a partir da `main` no commit `3add7d1127387d616abcc7b95a2a717c009a3d1f`.

O CSV foi congelado no commit `3788ba26801b5423df3835f3f05292366e0a6ae7`, antes de qualquer execução do Router ou Planner sobre as perguntas. Seu SHA-256 é:

`47d29dfaa0e71ea4b9c7c813b02d1001fa32a7605a241f95708686718a5b7ec7`

O fluxo congelado é:

- Router 1.2.0 — blob Git `f4236a7352e9b8808a22cf7d27c0efb1d4123821`;
- Retrieval Planner 1.1.0 — blob Git `2f5765a9ba70730b1af7f84ff4fc288eb3a2b96a`;
- Knowledge 1.2.0.

O manifesto `data/manifests/joint_retrieval_holdout_2_0_0.json` registra o freeze e mantém a primeira medição vazia até que os preflights sejam concluídos.

## Composição

São 40 perguntas:

| Categoria | Casos |
|---|---:|
| normative | 10 |
| methodology | 10 |
| cross_source | 14 |
| control_external | 6 |

Rotas esperadas:

| Rota | Casos |
|---|---:|
| knowledge | 17 |
| methodology | 10 |
| composite | 13 |

O conjunto referencia 29 documentos do corpus governado, dos quais 28 aparecem como gabarito principal. Dois casos são explicitamente sensíveis à vigência.

## Independência

A independência buscada é **avaliativa**, e não independência do corpus. O sistema continua consultando o mesmo corpus Knowledge 1.2.0, pois trocar simultaneamente perguntas e fontes confundiria a interpretação do resultado.

As perguntas do holdout, contudo, não foram utilizadas no tuning do Router 1.2.0 nem do Planner 1.1.0. O preflight compara as formulações normalizadas com cinco conjuntos anteriores:

- Assistant Benchmark 1.0.0;
- Router Holdout 1.0.0;
- Router Holdout 2.0.0;
- Retrieval Benchmark 1.0.0;
- Retrieval Planner Holdout 1.0.0.

Repetição exata normalizada é proibida. A similaridade de sequência mais alta é registrada apenas como diagnóstico descritivo, sem um limiar pós-hoc escolhido a partir do desempenho.

## Casos cross-source

A maior expansão de dificuldade está nos 14 casos `cross_source`. O conjunto inclui combinações que não estavam presentes como gate independente anterior, entre elas:

- literatura científica + norma vigente;
- metodologia de auditoria + orientação institucional;
- metodologia + normas oficiais do CPGF;
- controle externo + metodologia;
- controle externo + normas primárias.

Essa composição é intencional. Um assistente voltado ao controle social não deve apenas reconhecer perguntas normativas ou metodológicas isoladas; deve preservar os universos de evidência quando o usuário combina perspectivas em uma mesma consulta.

## Métricas da primeira medição

A primeira medição deve registrar, sem tuning posterior neste incremento:

- route exact match;
- scope exact match;
- temporal exact match;
- joint exact match (`route + scope + temporal`);
- resultados por categoria;
- matriz de confusão de rotas;
- IDs de divergência;
- recall e precisão de escopo e temporalidade;
- `trail_hints` apenas como diagnóstico secundário.

O resultado deve ser preservado integralmente, inclusive se for substancialmente inferior aos 100% obtidos nos conjuntos conhecidos após tuning.

## O que não será medido neste gate

Este gate não chama LLM, não executa SQL e não utiliza embeddings externos. Os `gold_document_ids` e `supporting_document_ids` são congelados agora para permitir uma avaliação posterior do Retriever sobre exatamente o mesmo conjunto, sem reescrever o oráculo depois de observar o desempenho de roteamento e planejamento.

## Regra após a primeira medição

Depois da primeira medição válida:

- `src/cpgf/ai/router.py` não pode ser alterado neste PR;
- `src/cpgf/ai/retrieval_planner.py` não pode ser alterado neste PR;
- perguntas e oráculos do CSV não podem ser alterados para elevar métricas;
- qualquer erro observado deve ser documentado como evidência de generalização e, se for usado futuramente para tuning, este holdout passa a ser regressão conhecida;
- uma nova alegação de generalização após novo tuning exigirá outro holdout independente.
