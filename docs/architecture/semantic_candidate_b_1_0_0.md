# Candidata Semântica B 1.0.0

## Finalidade

Este incremento congela formalmente a arquitetura `B_llm_route`, selecionada no Experimento de Arquitetura Semântica 1.0.1 sobre o JH4 já conhecido, antes da autoria de qualquer pergunta do Joint Holdout 5.0.0.

A seleção decorre da primeira medição real do protocolo 1.0.1, na qual B apresentou exatidão conjunta média de 54,86%, contra 37,50% da arquitetura determinística, com estabilidade modal de 98,61% e zero violações de schema. Esses números sustentam apenas a seleção de uma candidata; não constituem evidência de generalização.

## Arquitetura congelada

O fluxo candidato é:

`pergunta -> GPT-4o mini (somente rota) -> Retrieval Planner 1.3 -> rota + escopos + temporalidades`

O LLM recebe somente a pergunta e escolhe uma rota dentro do vocabulário fechado `knowledge`, `methodology` ou `composite`. Ele não decide escopos, temporalidades, documentos, resposta final ou resultado de auditoria. O Planner 1.3 permanece responsável pelos filtros de recuperação.

A execução é congelada com:

- modelo `gpt-4o-mini-2024-07-18`;
- OpenAI Responses API;
- OpenAI SDK 3.1.0;
- Python 3.12 para a medição independente;
- Structured Outputs estrito;
- três repetições;
- `store=false`;
- nenhuma ferramenta externa;
- Retriever e SQL desabilitados nesta etapa.

O Provider, o Planner e a dependência do tipo `Route` são protegidos por hashes Git blob. O manifesto de medição que originou a seleção também é protegido por hash.

## Desenho prospectivo do JH5

O JH5 será escrito somente após este freeze. Terá 48 perguntas, balanceadas em quatro categorias com 12 casos cada: `normative`, `methodology`, `cross_source` e `control_external`. A distribuição prospectiva de rotas será 24 `knowledge`, 12 `methodology` e 12 `composite`.

O benchmark não poderá repetir exatamente nenhuma pergunta dos benchmarks anteriores e deverá apresentar similaridade máxima SequenceMatcher de 0,70 em relação a qualquer pergunta prévia. Rota, escopos e temporalidades-gabarito serão definidos antes da primeira execução da candidata. As saídas da candidata não poderão ser consultadas durante a autoria do JH5.

## Gate prospectivo de generalização

A candidata somente ultrapassará o gate amplo do JH5 se todos os critérios abaixo forem atendidos:

1. as três repetições LLM forem concluídas;
2. ocorrerem zero violações de schema;
3. exatidão conjunta média de B >= 50%;
4. ganho conjunto absoluto de B sobre A >= 10 pontos percentuais;
5. exatidão média de rota de B >= 75%;
6. estabilidade modal média de B >= 0,90;
7. exatidão conjunta média de B em cada uma das quatro categorias >= 25%.

Os limiares são regras de governança do projeto, não testes de significância estatística. Um resultado parcialmente positivo poderá ser descrito, mas não substituirá o gate predefinido.

## Governança

A candidata não está ativada em produção. Após o início da autoria do JH5, não serão permitidas mudanças de prompt, modelo, Planner ou contrato de saída antes da primeira medição independente. O JH5 deverá ser congelado e passar por preflight antes que a candidata seja executada sobre qualquer uma de suas perguntas.

Se o JH5 falhar, o resultado será preservado. A avaliação independente do Retriever continuará bloqueada até que o gate da candidata seja examinado.
