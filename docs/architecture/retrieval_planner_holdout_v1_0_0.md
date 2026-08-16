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
- zero repetição exata normalizada das 30 perguntas do Retrieval Benchmark 1.0.0;
- 24 documentos-gabarito distintos;
- 25 documentos referenciados;
- 2 casos sensíveis à vigência.

O conjunto reutiliza documentos do corpus governado. O objetivo não é ampliar o corpus, mas testar se o planner generaliza seus filtros para novas formas linguísticas sobre o mesmo domínio documental.

## Protocolo

A avaliação compara, somente após o planejamento, os `scopes` e `temporal_statuses` inferidos pelo Planner 1.0.0 com os valores esperados do holdout. O planner recebe apenas a pergunta e a rota produzida pelo Router 1.1.0; não recebe gabaritos, IDs de documentos, escopos esperados ou temporalidade esperada.

As métricas são exact match de escopo, exact match de temporalidade, exact match conjunto, recall e precisão médios de escopo e recall e precisão médios de temporalidade.

## Primeira medição válida

A primeira execução que ultrapassou todos os preflights foi o run `31963655100`, no head `8e62070332314dc6b4b176ec82c216d9b3b943bc`, e terminou com `success`.

| Métrica | Resultado |
|---|---:|
| Escopo exato | 20/30 = 66,67% |
| Temporalidade exata | 14/30 = 46,67% |
| Concordância conjunta | 14/30 = 46,67% |
| Recall médio de escopo | 70,00% |
| Precisão média de escopo | 73,33% |
| Recall médio temporal | 56,67% |
| Precisão média temporal | 66,67% |

Foram preservadas 16 divergências: `KRET-102`, `KRET-107`, `KRET-108`, `KRET-113`, `KRET-114`, `KRET-115`, `KRET-116`, `KRET-117`, `KRET-118`, `KRET-119`, `KRET-120`, `KRET-123`, `KRET-126`, `KRET-127`, `KRET-128` e `KRET-129`.

A distribuição de rotas observada foi 12 `knowledge`, 9 `overview`, 1 `trails` e 8 `unsupported`. Esse dado é relevante para interpretar a queda em relação ao conjunto de desenvolvimento: o Planner recebe a rota do Router 1.1.0, e várias formulações documentais novas já chegaram ao planner com rotas `overview`, `trails` ou `unsupported`. Portanto, a concordância de 46,67% caracteriza o fluxo efetivamente testado `Router 1.1.0 -> Planner 1.0.0`; não é metodologicamente correto atribuir todas as divergências exclusivamente às regras internas do Planner.

Os erros se concentraram principalmente em três padrões. Primeiro, perguntas metodológicas frequentemente deixaram de receber `methodology` e `contextual`, recaindo em `cpgf_core/current`. Segundo, casos que combinavam fontes normativas e científicas frequentemente preservaram apenas `current`, omitindo a camada `contextual`. Terceiro, uma nova formulação de controle externo foi roteada como `overview` e, por consequência, recebeu `cpgf_core/current`, embora outras duas formulações do mesmo domínio tenham sido corretamente reconhecidas como `control_external/contextual`.

## Evidência

- workflow: `retrieval-planner-holdout-smoke`;
- run: `31963655100` — PASS;
- job: `95205360724`;
- artifact ID: `9267891103`;
- digest do artifact ZIP: `sha256:4145718900ff3939b0158ccaac43c22571a3803a739d387ed36b553efa891d8b`;
- CI no mesmo head: run `31963651033`, Python 3.11 e 3.12 com Ruff + pytest — PASS.

## Leitura metodológica

O Retrieval Benchmark conhecido havia produzido concordância conjunta de 29/30 = 96,67% para o Planner 1.0.0. O novo holdout produziu 14/30 = 46,67%. Como os conjuntos contêm perguntas diferentes, a diferença não é uma comparação pareada nem uma estimativa formal de perda de acurácia. Ainda assim, a medição revela fragilidade de generalização suficiente para impedir que o resultado conhecido de 96,67% seja interpretado como desempenho esperado em novas formulações.

Antes de ajustar o Planner, o diagnóstico seguinte deve separar explicitamente a contribuição do Router e a contribuição do Planner. Isso evita corrigir regras de recuperação para compensar erros que surgem na classificação de intenção e preserva a separação arquitetural entre roteamento e planejamento documental.

## Governança

O holdout não é usado para ajustar o Planner 1.0.0 neste incremento. Se seus erros forem utilizados para desenvolver uma versão posterior do Router ou do Planner, este conjunto deixa de representar dados não usados no ajuste dessas versões e passa a funcionar como regressão conhecida. Uma nova alegação de generalização exigirá outro conjunto independente.

A medição não representa qualidade final de resposta de LLM, relevância documental absoluta ou acurácia de produção. Não houve chamada a LLM, execução de SQL, alteração de T01–T09, Motor, Serving, Geo ou Knowledge.
