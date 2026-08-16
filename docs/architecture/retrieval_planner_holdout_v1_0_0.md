# Retrieval Planner Holdout 1.0.0

## Objetivo

Avaliar o Retrieval Planner 1.0.0 em formulações novas, criadas após o congelamento da implementação do planner e distintas por correspondência exata normalizada do Retrieval Benchmark 1.0.0 usado no desenvolvimento.

O incremento é deliberadamente avaliativo. Ele não altera `src/cpgf/ai/retrieval_planner.py` e não corrige erros observados no holdout.

## Congelamento

O arquivo `data/benchmarks/retrieval_planner_holdout_v1_0_0.csv` contém 30 perguntas. A primeira versão estruturalmente válida do CSV foi congelada no commit `0b8fdb36f17a370ef3d47c979798936cc46c1ce4`.

SHA-256: `ec17f7b2c4c93ae862f0796bfd7a1380b64409fa5270c67b7f00625f1f88a667`.

As correções anteriores ao congelamento válido foram exclusivamente de serialização CSV: perguntas que continham vírgulas internas precisaram ser delimitadas por aspas. Não houve alteração de texto, categoria, gabarito documental, escopo esperado, temporalidade esperada ou trilhas esperadas para elevar desempenho.

## Preflights inválidos

Duas tentativas automatizadas foram encerradas antes da chamada a `evaluate_retrieval_planner()`:

- run `31963293358`: divergência entre a constante de SHA-256 e os bytes versionados;
- run `31963454354`: falha de validação de esquema causada por vírgulas internas ainda não escapadas em algumas perguntas.

Nenhum dos dois runs constitui medição do Planner 1.0.0. O congelamento metodológico válido passa a ser o commit e o SHA-256 informados acima.

## Composição

- 13 casos normativos;
- 8 casos de combinação de fontes;
- 6 casos metodológicos;
- 3 casos de controle externo;
- IDs `KRET-101` a `KRET-130`;
- zero repetição exata normalizada das 30 perguntas do Retrieval Benchmark 1.0.0.

O conjunto reutiliza documentos do corpus governado. O objetivo não é ampliar o corpus, mas testar se o planner generaliza seus filtros para novas formas linguísticas sobre o mesmo domínio documental.

## Protocolo

A avaliação compara, somente após o planejamento, os `scopes` e `temporal_statuses` inferidos pelo Planner 1.0.0 com os valores esperados do holdout. O planner recebe apenas a pergunta e a rota produzida pelo Router 1.1.0; não recebe gabaritos, IDs de documentos, escopos esperados ou temporalidade esperada.

As métricas são:

- exact match de escopo;
- exact match de temporalidade;
- exact match conjunto;
- recall e precisão médios de escopo;
- recall e precisão médios de temporalidade.

## Governança

O holdout não deve ser usado para ajustar o Planner 1.0.0 neste incremento. Se seus erros forem utilizados para desenvolver uma versão posterior, este conjunto deixa de representar dados não usados no ajuste dessa nova versão e passa a funcionar como regressão conhecida. Uma nova alegação de generalização exigirá outro conjunto independente.

A medição não representa qualidade final de resposta de LLM, relevância documental absoluta ou acurácia de produção.
