# Retrieval Planner 1.3.0

## Objetivo

O Retrieval Planner 1.3.0 é um incremento determinístico sobre o Planner 1.2.0. O objetivo é melhorar a seleção de `scopes` e `temporal_statuses` para formulações documentais já identificadas no diagnóstico pós-hoc do Joint Holdout 3.0, mantendo o Router 1.4.0 congelado.

Este incremento não altera o Retriever, não executa SQL, não usa embeddings externos e não chama LLM.

## Contexto experimental

A primeira medição independente do Joint Holdout 3.0 foi realizada com Router 1.3.0 e Planner 1.2.0 e obteve 27/48 no critério conjunto de rota, escopo e temporalidade.

O diagnóstico pós-hoc atribuiu participação do Planner em nove falhas. Após o tuning exclusivo do Router 1.4.0, as 48 rotas passaram a coincidir com o gabarito congelado, enquanto o fluxo conjunto ficou em 39/48. Restaram nove casos de filtros:

- JH3-003
- JH3-027
- JH3-028
- JH3-029
- JH3-030
- JH3-033
- JH3-034
- JH3-036
- JH3-037

Esses IDs documentam a regressão conhecida, mas não são usados por nenhuma regra operacional.

## Famílias semânticas ampliadas

O Planner 1.3.0 amplia apenas reconhecedores gerais:

1. **Instrumentalidade jurídica do cartão** — formulações que perguntam se o meio de pagamento altera a classificação ou natureza da despesa passam a admitir evidência normativa atual e literatura interpretativa contextual quando necessário.
2. **Fonte normativa + estudo interpretativo** — perguntas que explicitam a leitura conjunta de base normativa e estudo são tratadas como ponte documental sem inferir escopos adicionais desnecessários.
3. **Competência e educação informacional** — capacidade de interpretação, educação informacional e participação social passam a compor corretamente o escopo metodológico quando aparecem junto ao CPGF ou a dados do cartão.
4. **Metodologia + orientação institucional** — literatura metodológica, análise quantitativa, padrões digitais e sinais analíticos combinados a orientação oficial/institucional passam a recuperar `methodology` e `cpgf_core` com temporalidades contextual e current.
5. **Controle externo + enquadramento normativo** — decisões ou pronunciamentos do Tribunal de Contas combinados a diplomas estruturantes, regime de adiantamento ou enquadramento jurídico passam a recuperar `control_external` e `cpgf_core`.
6. **Controle externo + metodologia** — fontes de controle externo combinadas a estudos metodológicos, sinal automatizado, triagem ou verificação passam a recuperar `control_external` e `methodology`.
7. **Tribunal de Contas em formulação temática** — a identificação de controle externo deixa de depender exclusivamente da sigla `TCU` ou da forma extensa `Tribunal de Contas da União`.

## Isolamento

O Router 1.4.0 permanece congelado no blob:

`89150b97e9c87d9af0d0b0f888870dcc74ef86b1`

O Planner 1.2.0 histórico permanece preservado no blob:

`7ee30359cb4457b0bd1a12b43d14f73be410ddaa`

O Planner 1.3.0 medido corresponde ao blob:

`8fa1458c11eeabfdde155635b74a9b770e9960c1`

## Resultado em regressões conhecidas

Na primeira regressão válida do comportamento 1.3.0:

- Retrieval Benchmark: 30/30;
- Retrieval Planner Holdout 1: 30/30;
- Joint Holdout 2: 40/40 no critério conjunto;
- Joint Holdout 3: 48/48 em rota, escopo, temporalidade e critério conjunto.

A regressão foi reproduzida de forma idêntica em Python 3.11 e 3.12. Os JSONs de evidência têm SHA-256 comum:

`7600790addec6b5261f54f5fd6a8b4bf119b31c635b3ba2d19d02f3b56f735b0`

O primeiro CI do PR não produziu medição semântica porque o avaliador utilizou nomes incorretos para campos do baseline histórico do manifesto do Router 1.4. O erro foi corrigido apenas no harness; as regras do Planner não mudaram entre essa falha estrutural e a primeira regressão válida.

## Interpretação

O resultado 48/48 é uma regressão conhecida, pois o JH3 já havia sido medido, diagnosticado e utilizado para orientar o tuning. Portanto, não constitui nova evidência de generalização e não deve ser comparado como se fosse uma nova medição independente.

O resultado relevante para generalização continua sendo a primeira medição independente congelada do JH3: 27/48 com Router 1.3.0 e Planner 1.2.0.

## Próximo gate

Após a estabilização do Planner 1.3.0, a próxima avaliação de generalização deve usar um **Joint Holdout 4.0 independente**, criado e congelado antes de qualquer execução do Router 1.4.0 + Planner 1.3.0 sobre suas perguntas.

O novo holdout deve preservar novidade contra todos os benchmarks anteriores, inclusive JH2 e JH3, e registrar critérios prospectivos antes da primeira medição.

A avaliação do Retriever permanece uma etapa separada. O resultado do Router + Planner, por si só, não sustenta prontidão de produção nem desbloqueia integração com LLM.
