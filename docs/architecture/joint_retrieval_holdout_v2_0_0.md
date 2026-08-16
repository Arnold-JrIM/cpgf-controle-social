# Joint Retrieval Holdout 2.0.0

## Finalidade

O Joint Retrieval Holdout 2.0.0 é o primeiro conjunto criado **depois** do congelamento conjunto do Router 1.2.0 e do Retrieval Planner 1.1.0. Seu objetivo é produzir nova evidência de generalização do fluxo documental, sem reutilizar o conjunto que orientou o tuning dessas versões.

Cada pergunta contém três componentes independentes do oráculo:

1. `expected_route` — intenção documental que o Router deve selecionar;
2. `expected_scopes` — universos documentais que o Planner deve habilitar;
3. `expected_temporal_statuses` — combinação de fontes correntes e/ou contextuais.

A métrica principal é a concordância exata conjunta desses três elementos.

## Freeze antes da medição

O benchmark foi criado a partir da `main` no commit `3add7d1127387d616abcc7b95a2a717c009a3d1f`.

O primeiro commit do CSV, `3788ba26801b5423df3835f3f05292366e0a6ae7`, continha apenas uma falha de serialização CSV: campos textuais com vírgulas não estavam escapados de forma uniforme. O preflight falhou antes de qualquer chamada ao Router ou Planner. Nenhuma pergunta, categoria, rota esperada, escopo, temporalidade, trilha ou documento-gabarito foi alterado.

A serialização canônica foi congelada no commit `d5bd22029e161c5a20722bdfbe638ec51a92da60`. Seu SHA-256 é:

`47d29dfaa0e71ea4b9c7c813b02d1001fa32a7605a241f95708686718a5b7ec7`

O fluxo congelado é:

- Router 1.2.0 — blob Git `f4236a7352e9b8808a22cf7d27c0efb1d4123821`;
- Retrieval Planner 1.1.0 — blob Git `2f5765a9ba70730b1af7f84ff4fc288eb3a2b96a`;
- Knowledge 1.2.0.

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

## Independência avaliativa

A independência buscada é **avaliativa**, e não independência do corpus. O sistema continua consultando o mesmo Knowledge 1.2.0, pois trocar simultaneamente perguntas e fontes confundiria a interpretação do resultado.

As perguntas não foram utilizadas no tuning do Router 1.2.0 nem do Planner 1.1.0. O preflight comparou as formulações normalizadas com cinco conjuntos anteriores, totalizando 190 perguntas. Não houve repetição exata normalizada. A maior similaridade de sequência foi aproximadamente 0,832 e foi preservada apenas como diagnóstico; nenhum limiar foi escolhido depois de observar o desempenho.

## Casos cross-source

A maior expansão de dificuldade está nos 14 casos `cross_source`. O conjunto inclui combinações que não estavam presentes como gate independente anterior, entre elas:

- literatura científica + norma vigente;
- metodologia de auditoria + orientação institucional;
- metodologia + normas oficiais do CPGF;
- controle externo + metodologia;
- controle externo + normas primárias.

Essa composição é intencional. Um assistente voltado ao controle social não deve apenas reconhecer perguntas normativas ou metodológicas isoladas; deve preservar os universos de evidência quando o usuário combina perspectivas em uma mesma consulta.

## Primeira medição independente

A primeira medição válida ocorreu no workflow `31967548985`, head `662cdee4c54c04f082647e640b9e4822019e209a`, em Python 3.11, job `95214916177`.

O artefato `9268901430` tem digest:

`sha256:22c426db9f28cec1e07f13ef09b3a1c92992655fdc323565032e93cc2e7a2ea2`

Resultado global:

| Métrica | Resultado |
|---|---:|
| Rota exata | 13/40 = **32,5%** |
| Escopo exato | 26/40 = **65,0%** |
| Temporalidade exata | 24/40 = **60,0%** |
| Rota + escopo + temporalidade | 12/40 = **30,0%** |
| Recall médio de escopo | **76,25%** |
| Precisão média de escopo | **83,75%** |
| Recall médio temporal | **71,25%** |
| Precisão média temporal | **82,50%** |

Por categoria:

| Categoria | Rota exata | Escopo exato | Temporal exata | Conjunto exato |
|---|---:|---:|---:|---:|
| normative | 7/10 | 10/10 | 9/10 | **7/10 = 70,0%** |
| methodology | 2/10 | 3/10 | 4/10 | **2/10 = 20,0%** |
| cross_source | 2/14 | 7/14 | 5/14 | **1/14 = 7,14%** |
| control_external | 2/6 | 6/6 | 6/6 | **2/6 = 33,33%** |

A reprodução em Python 3.12, job `95214997173`, gerou o artefato `9268909720`, digest `sha256:54daecc256c82f32065c0b926c5feeebc9b5ea8c2b6703c5b6eaacee9ef703eb`. Resumo global, métricas por categoria, matriz de confusão e IDs divergentes coincidiram exatamente com Python 3.11.

## Leitura técnica

O resultado é substancialmente inferior aos 100% observados nos dois conjuntos conhecidos após tuning. Essa diferença não deve ser interpretada como uma comparação pareada de acurácia, pois os conjuntos têm perguntas diferentes. Ainda assim, o novo holdout fornece evidência direta de **fragilidade de generalização** e impede tratar o desempenho dos conjuntos conhecidos como expectativa de produção.

A maior fragilidade aparece no roteamento. Das 13 perguntas cujo oráculo esperava `composite`, apenas uma recebeu essa rota; sete foram encaminhadas como `knowledge`. Nas dez perguntas metodológicas, apenas duas receberam `methodology`. Em quatro das seis consultas de controle externo, o Planner reconheceu corretamente `control_external/contextual`, mas o Router classificou a pergunta como `unsupported`, mostrando que filtros corretos podem coexistir com orquestração inadequada.

Nos 28 casos que falharam na métrica conjunta, uma decomposição **meramente descritiva**, e não causal, encontrou:

- 9 casos com rota divergente e filtros exatos;
- 1 caso com rota exata e filtros divergentes;
- 18 casos com divergência tanto de rota quanto de filtros;
- 12 passes limpos.

Essa contagem não deve ser tratada como atribuição causal Router versus Planner. Uma separação causal exigiria diagnóstico contrafactual específico, variando a rota enquanto mantém pergunta e oráculo congelados, à semelhança do procedimento já empregado em incrementos anteriores.

## Implicação de governança

O Joint Retrieval Holdout 2.0.0 passou a ser **conhecido** depois da primeira medição. Portanto:

- o resultado 12/40 deve ser preservado, não corrigido neste PR;
- `src/cpgf/ai/router.py` não será alterado neste incremento;
- `src/cpgf/ai/retrieval_planner.py` não será alterado neste incremento;
- perguntas e oráculos não serão reescritos para elevar métricas;
- o resultado constitui nova evidência de generalização, mas **não sustenta prontidão para produção**;
- a ativação do LLM permanece bloqueada;
- se os erros forem utilizados para tuning futuro, este holdout passa a servir somente como regressão conhecida;
- qualquer nova alegação de generalização após tuning exigirá outro holdout independente.

## Próximo gate

O passo metodologicamente adequado é um incremento separado de **diagnóstico post-hoc**, sem tuning, para decompor as falhas entre Router, Planner e interação entre as duas camadas. Só depois dessa decomposição devem ser planejadas novas versões das regras.

A avaliação do Retriever também permanece separada. Os `gold_document_ids` e `supporting_document_ids` já estão congelados para que a recuperação documental possa ser medida futuramente sem reescrever o oráculo após observar o resultado do fluxo Router -> Planner.
