# Retrieval Planner 1.1.0

## Finalidade

O Retrieval Planner 1.1.0 refina a inferência determinística de filtros documentais entre o Router 1.2.0 e o Knowledge Retriever. O incremento corrige padrões observados em conjuntos já conhecidos, sem usar LLM, sem executar SQL e sem modificar o Router ou as trilhas T01–T09.

O fluxo permanece:

`pergunta -> Router 1.2.0 -> Retrieval Planner 1.1.0 -> Retriever -> evidências`

## Motivação

Após o tuning do Router 1.2.0, o Retrieval Planner 1.0.0 acertava conjuntamente escopo e temporalidade em 21 dos 30 casos do antigo Retrieval Planner Holdout 1.0.0. Nove divergências permaneceram atribuídas ao Planner e passaram a constituir material de desenvolvimento conhecido.

Os erros se concentravam em três problemas semânticos: subestimação da necessidade de combinar fontes atuais e contextuais, falta de reconhecimento de algumas paráfrases de controle social/controle externo e dependência excessiva de palavras literais como `fracionamento` ou `Benford`.

## Alterações

As regras do Planner 1.1.0 foram ampliadas por classes linguísticas gerais, sem qualquer condição baseada em IDs `KRET-*`:

- natureza jurídica e caráter instrumental do cartão;
- literatura acadêmica combinada com regime vigente de contratação ou licitação;
- controle social vinculado explicitamente ao CPGF, cartão governamental ou Portal da Transparência;
- controle externo e fiscalização continuada em formulações que não citam necessariamente `TCU` ou `acórdão`;
- aquisições semelhantes, recorrentes ou em sequência como paráfrases relevantes para análise de possível divisão indevida da despesa;
- ampliação dos `trail_hints` de T08 e T09, que continuam diagnósticos e não confirmam irregularidade.

## Regressão conhecida

Dois conjuntos já conhecidos foram usados exclusivamente como desenvolvimento/regressão:

| Conjunto | Planner 1.1.0 |
|---|---:|
| Retrieval Benchmark 1.0.0 | 30/30 filtros conjuntos exatos |
| Retrieval Planner Holdout 1.0.0 | 30/30 filtros conjuntos exatos |

Em ambos, escopo, temporalidade, recall e precisão dos filtros ficaram em 100% no conjunto conhecido. Esses números **não são uma estimativa de desempenho em produção nem uma nova evidência de generalização**.

A primeira execução válida dessa regressão ocorreu no head `4e2f872b38f078609fdb9f678c38875e6d0f042d`, workflow `retrieval-planner-v1.1-regression`, run `31966123250`, com sucesso em Python 3.11 e 3.12.

## Linha histórica preservada

A evolução deve ser interpretada em três momentos diferentes:

1. Router 1.1.0 + Planner 1.0.0, no primeiro holdout independente: 14/30;
2. Router 1.2.0 + Planner 1.0.0, após tuning do Router em dados já conhecidos: 21/30;
3. Router 1.2.0 + Planner 1.1.0, após tuning do Planner no mesmo material agora conhecido: 30/30.

Somente o primeiro momento foi uma medição independente daquele holdout. Os dois resultados posteriores são regressão de desenvolvimento.

Por isso, o workflow histórico do Router 1.2.0 foi desacoplado da versão corrente do Planner. O resultado 21/30 continua registrado com `planner_version_held_fixed = 1.0.0` no manifesto do Router; ele não é recalculado com o Planner 1.1.0.

## Governança

- Router permanece em 1.2.0;
- Planner passa a 1.1.0;
- nenhuma regra específica por ID de benchmark;
- nenhuma chamada a LLM;
- nenhum SQL;
- nenhuma alteração em Motor, Serving, Geo, Knowledge ou T01–T09;
- o antigo holdout foi consumido pelo tuning e não pode mais sustentar alegação independente;
- o resultado 60/60 é classificado como `KNOWN_REGRESSION_ONLY`.

## Próximo gate

O próximo incremento metodológico não deve realizar novo tuning. Deve criar **um novo holdout conjunto independente**, com novas formulações documentais e de intenção, depois do congelamento de Router 1.2.0 + Planner 1.1.0 e antes de sua primeira medição.

Esse novo conjunto deve avaliar o fluxo completo de roteamento e planejamento sem alterar regras após o congelamento inicial. Somente então será possível estimar novamente a generalização do pipeline e decidir, com base em evidência externa aos conjuntos de tuning, se a camada conversacional/LLM pode avançar para integração controlada.
