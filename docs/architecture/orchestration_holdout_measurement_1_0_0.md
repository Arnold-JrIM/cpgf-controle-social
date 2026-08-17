# Orchestration Holdout 1.0.0 — Measurement Harness 1.0.0

## Decisão

Este incremento congela o protocolo que fará a **primeira medição independente** do Semantic Evidence Orchestrator 1.0 sobre o Orchestration Holdout 1.0.0 (OH1). O holdout foi congelado e incorporado ao `main` no PR #67 antes de qualquer execução do `gpt-4o-mini` sobre suas 56 perguntas.

O PR do harness permanece estritamente **pré-medição**. Em `pull_request`, apenas testes offline são executados. A chamada real ao modelo ocorre somente depois do merge, por `push` do harness ao `main`.

## Unidade avaliada

A candidata congelada é o `Semantic Evidence Orchestrator 1.0`, cuja responsabilidade termina na criação do `EvidencePlan`. A avaliação não executa:

- Data Evidence Worker;
- Knowledge Evidence Worker;
- Web/Freshness Evidence Worker;
- Retriever;
- SQL ou DuckDB;
- Synthesizer;
- Evidence Verifier;
- resposta final ao usuário.

O objetivo é medir isoladamente se o Orchestrator identifica corretamente **quais fontes de evidência são necessárias** e se produz os parâmetros estruturados esperados.

## Modelo

A execução oficial usa exclusivamente a política central do projeto:

`DEFAULT_LLM_MODEL = "gpt-4o-mini"`

Não existe input de workflow para trocar modelo ou número de repetições. O provider continua usando Responses API, Structured Outputs estrito e `store=False`.

## Protocolo

O OH1 contém 56 casos e cobre, com oito casos cada, os sete conjuntos não vazios entre `DATA`, `KNOWLEDGE` e `WEB`.

A primeira medição executará:

- 56 casos;
- 3 repetições completas;
- 168 tentativas do Orchestrator;
- Python 3.12;
- OpenAI SDK 3.1.0.

Cada linha bruta preservará pergunta, gabarito, previsão, status de planejamento, conjunto de fontes, ferramenta e argumentos DATA, filtros KNOWLEDGE, parâmetros WEB, under/over-routing, response ID, modelo retornado, tokens, latência, warning e exatidões.

## Métricas prospectivas

O evaluator calcula:

- Evidence Source Set Exact Match;
- precisão e recall de seleção de fontes;
- under-routing e over-routing;
- seleção exata da ferramenta DATA;
- argumentos DATA exatos;
- filtros KNOWLEDGE conjuntamente exatos (`scope`, temporalidade e classe de fonte);
- parâmetros WEB exatos;
- full-plan exact;
- violações estruturais e falhas de provider/plano;
- estabilidade modal do plano estruturado nas três repetições;
- desempenho por categoria do holdout.

A assinatura usada para estabilidade exclui texto livre como `reason`, `objective` e `query_hint`. Ela considera somente a estrutura operacional relevante do plano, evitando punir variação linguística sem efeito de roteamento ou execução.

## Gate congelado

Os limiares foram definidos no PR #67 e são apenas reproduzidos no protocolo de medição. Todos são conjuntivos:

- Source Set Exact Match médio >= 0,65;
- precisão média de fontes >= 0,80;
- recall médio de fontes >= 0,80;
- ferramenta DATA exata >= 0,70;
- argumentos DATA exatos >= 0,60;
- filtros KNOWLEDGE conjuntamente exatos >= 0,50;
- parâmetros WEB exatos >= 0,70;
- estabilidade modal média >= 0,90;
- Source Set Exact Match >= 0,50 em cada categoria;
- zero violações de schema;
- três repetições completas.

Performance abaixo desses valores **não falha o workflow por desempenho**. Um resultado `FAIL` é resultado experimental válido e deverá ser preservado integralmente.

## Freeze por hash

Antes da primeira chamada real, o runner valida os Git blob SHAs congelados de:

- política de modelo;
- Semantic Orchestrator;
- contratos de evidência;
- Evidence Workers usados como superfície de capacidade DATA;
- `TOOL_REGISTRY`;
- política WEB;
- evaluator da medição;
- runner oficial.

Também valida o SHA-256 do benchmark comprimido e a versão do OpenAI SDK.

## Trigger da primeira medição

O workflow possui duas fronteiras:

1. `pull_request`: somente lint e testes offline, sem `OPENAI_API_KEY` e sem chamadas ao modelo;
2. `push` ao `main` contendo o harness: executa automaticamente a primeira medição oficial com o secret `OPENAI_API_KEY`.

Essa separação garante que o código de mensuração esteja revisado e incorporado ao `main` antes de observar qualquer saída do OH1.

## Governança após a execução

O primeiro resultado deverá ser preservado em incremento separado com:

- JSON bruto;
- gzip determinístico;
- SHA-256 do JSON e do gzip;
- run ID, job ID e commit;
- métricas e resultado do gate sem alteração retrospectiva.

Depois da primeira medição, OH1 passa a ser material conhecido. Qualquer tuning baseado em seus erros exigirá outro holdout prospectivo para uma nova alegação de independência.
