# Retrieval Planner Holdout 1.0.0

## Objetivo

Avaliar o Retrieval Planner 1.0.0 em formulações novas, criadas após o congelamento da implementação do planner e distintas por correspondência exata normalizada do Retrieval Benchmark 1.0.0 usado no desenvolvimento.

O incremento é deliberadamente avaliativo. Ele não altera `src/cpgf/ai/retrieval_planner.py` e não corrige erros observados no holdout.

## Congelamento

O arquivo `data/benchmarks/retrieval_planner_holdout_v1_0_0.csv` contém 30 perguntas e foi congelado, em sua primeira forma válida de esquema, no commit `e4b47b5376ff7b9b7f5768ab53f3ba5a6d464265`.

SHA-256: `ccbc8b89cb81027b41a380eceaa3ed127663a1d34fc23cf1060e54d1ddcdc480`.

O primeiro commit da branch continha uma única falha de serialização CSV: uma vírgula interna sem aspas em uma pergunta. O commit de congelamento válido corrigiu apenas essa serialização, sem modificar pergunta, categoria, gabarito documental, escopo esperado, temporalidade esperada ou trilhas esperadas.

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
