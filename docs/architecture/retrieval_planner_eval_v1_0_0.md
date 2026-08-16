# Avaliação do Retrieval Planner 1.0.0

## Escopo

Esta evidência registra a primeira medição do Retrieval Planner 1.0.0 sobre o Retrieval Benchmark 1.0.0. O código do planner foi congelado antes da execução e identificado pelo blob Git `6e6a0c7b6b1c39d1313b266f4ac7652ce69edc2f`.

A avaliação usa o mesmo benchmark e o mesmo corpus congelados nas avaliações anteriores:

- benchmark SHA-256 `6633babe7e17f4c0fefb0523ea477a11257bad87d3c0bc258dea7db1c33c1777`;
- chunks SHA-256 `43c7d61e8b963c5b8b1ad747ec24c2cdb5e464d403ea9b2b3776f19a5cb65b7c`;
- 30 casos, 24 documentos gold e 24/24 documentos gold com chunks;
- `k=5`;
- métodos lexical, semantic e hybrid.

O arquivo detalhado permanece local em `data/evidence/knowledge_retrieval/retrieval_planner_eval_v1_0_0.json`, com SHA-256 `b56380f54c5132de016181c01e78d72ab41c90fb09a294c03a629aa9fb4732b2`. O resultado integral não é versionado no Git.

## Qualidade do planejamento

O planner reproduziu corretamente o escopo documental em 30/30 casos. Para temporalidade, houve concordância exata em 29/30 casos. Em consequência:

| Métrica | Resultado |
|---|---:|
| Scope exact match | 100,00% |
| Temporal exact match | 96,67% |
| Joint exact match | 96,67% |
| Mean scope recall | 100,00% |
| Mean scope precision | 100,00% |
| Mean temporal recall | 98,33% |
| Mean temporal precision | 100,00% |

A única divergência ocorreu em `KRET-002`. O escopo `cpgf_core` foi preservado, mas o planner retornou apenas `current`, enquanto o gabarito também admitia `contextual`. Essa divergência é mantida como parte da evidência. Nenhuma regra do Planner 1.0.0 foi modificada após a observação do resultado.

## Recuperação documental em runtime

O cenário `runtime_governed` representa o caminho executável: a pergunta é roteada e o planner infere os filtros sem acesso ao oráculo. O cenário `governed` continua apenas como referência controlada, pois recebe diretamente os filtros esperados do benchmark.

| Método | Hit Rate@5 | Mean Document Recall@5 | MRR | MAP@5 |
|---|---:|---:|---:|---:|
| Lexical runtime | 86,67% | 69,44% | 0,6561 | 0,5240 |
| Semantic runtime | 96,67% | 89,44% | 0,7167 | 0,6782 |
| Hybrid runtime | 96,67% | 83,33% | 0,7344 | 0,6441 |

Nos métodos semantic e hybrid, as quatro métricas agregadas de `runtime_governed` foram idênticas às do cenário-oráculo. No lexical, Hit Rate@5 e Mean Document Recall@5 também foram idênticos; MRR e MAP@5 ficaram ligeiramente maiores no runtime porque a restrição temporal mais estreita em `KRET-002` elevou o documento gold de posição. Essa variação é incidental neste conjunto e não deve ser interpretada como evidência de que a divergência temporal seja desejável.

## Efeito da governança inferida

Comparado ao cenário `unfiltered`, o planner melhorou a recuperação em diferentes dimensões:

| Método | Δ Hit@5 | Δ Recall@5 | Δ MRR | Δ MAP@5 |
|---|---:|---:|---:|---:|
| Lexical | +0,1333 | +0,1444 | +0,0867 | +0,0797 |
| Semantic | +0,0000 | +0,0611 | +0,0478 | +0,0769 |
| Hybrid | +0,0333 | +0,0778 | +0,0322 | +0,0709 |

O efeito foi especialmente visível na recuperação lexical, em que a redução do universo documental aumentou tanto cobertura quanto ordenação. No semantic, o Hit Rate@5 já era elevado sem filtro, mas a governança aumentou recall documental, MRR e MAP@5. No hybrid, houve ganho nas quatro métricas.

## Comparação entre métodos

No cenário executável `runtime_governed`, semantic e hybrid atingiram Hit Rate@5 de 96,67%. Semantic apresentou o maior Mean Document Recall@5 (89,44%) e o maior MAP@5 (0,6782), enquanto hybrid apresentou o maior MRR (0,7344). Portanto, esta medição não sustenta uma única escolha dominante para todos os critérios.

`KRET-004` permaneceu sem documento gold no top 5 tanto em semantic quanto em hybrid. O caso é preservado como falha observada; o benchmark e seus golds não são alterados em resposta ao resultado.

## Telemetria e governança

A avaliação semântica reutilizou o índice previamente construído e efetuou 30 requisições externas para embeddings das 30 perguntas, com `text-embedding-3-small`, dimensão 768 e cache de consulta habilitado. Não houve chamada de LLM nem execução de SQL.

O planner recebe somente a pergunta e a decisão do Router. O benchmark-oráculo é usado exclusivamente após a geração do plano, para avaliação. O cenário-oráculo permanece no relatório como upper bound comparativo e não é uma simulação de produção.

## Limitação de validade

O Retrieval Benchmark 1.0.0 já era conhecido durante o desenvolvimento das regras do Planner 1.0.0. Assim, os resultados desta página constituem **diagnóstico de desenvolvimento/in-sample**, e não evidência de generalização.

A política de recuperação de produção não deve ser escolhida com base apenas nesta medição. O próximo gate metodológico é um holdout novo, construído após o congelamento do Planner 1.0.0, no qual nenhuma regra desta versão seja alterada antes da primeira avaliação.
