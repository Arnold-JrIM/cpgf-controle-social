# Orchestration Holdout 2.0.0 — freeze prospectivo

## Status

**FROZEN_BEFORE_MEASUREMENT**

O OH2 é o novo conjunto prospectivo para avaliar o `Semantic Evidence Orchestrator 1.1.0`
com a camada governada de normalização `1.0.0`. O candidato foi congelado no `main`
`b3db0407c7c57ad9be76d631f0b32dd960efadbb`, após o merge do PR #71.

O OH1 já foi medido, tornou-se conhecido e não pode ser reutilizado como evidência independente
de generalização. Por isso, nenhuma saída do candidato sobre as perguntas do OH2 é produzida
durante a autoria ou o preflight deste freeze.

## Desenho

O benchmark contém **56 casos novos**, distribuídos igualmente entre sete categorias:

- `data_only`;
- `knowledge_only`;
- `web_only`;
- `data_knowledge`;
- `knowledge_web`;
- `data_web`;
- `all_three`.

Cada categoria contém oito casos. Em consequência, `DATA`, `KNOWLEDGE` e `WEB` aparecem
exatamente em 32 casos cada.

Os oráculos congelam o conjunto de fontes requerido e, quando aplicável:

- ferramenta DATA e argumentos Pydantic já normalizados com defaults;
- `scopes`, `temporal_statuses` e `source_classes` de KNOWLEDGE;
- `limit`, `official_only=true` e janela explícita `max_age_days` para WEB.

O desenho inclui consultas compostas com números que pertencem a componentes diferentes da
pergunta, por exemplo top-N em DATA combinado com janela temporal de WEB. Isso testa a separação
de parâmetros sem introduzir execução de ferramentas no freeze.

## Universo de novidade

A comparação histórica é **explicitamente congelada** e não descoberta dinamicamente. O OH2 é
comparado contra 10 benchmarks anteriores, totalizando 430 perguntas, incluindo
`orchestration_holdout_v1_0_0.csv.gz`.

O gate exige:

- zero repetição exata após normalização;
- similaridade máxima por `SequenceMatcher` de **0,70** contra o universo histórico congelado.

Novos benchmarks adicionados no futuro não alteram retroativamente a evidência prospectiva deste
freeze.

## Candidato congelado

O freeze preserva, por hash de blob e versão, as fronteiras que determinam o significado do plano:

- Semantic Orchestrator `1.1.0` e policy `1.1.0`;
- normalização pós-LLM `1.0.0`;
- Evidence Contracts `1.0.0`;
- Evidence Workers `1.0.0`;
- Web Evidence Worker/Policy `1.0.0`;
- política de modelo `1.0.0`;
- contratos das ferramentas DATA;
- enums e contratos de KNOWLEDGE;
- TOOL_REGISTRY;
- `pyproject.toml`.

O modelo governado permanece exclusivamente **`gpt-4o-mini`**. O hash SHA-256 do prompt do
Orchestrator permanece `9255a15213b96a9ba219fd43fb402e8d797842064c73d5a9e629d73f0b3269c2`.

## Preflight

O workflow `orchestration-holdout-v2-preflight` executa somente validações offline em Python
3.11 e 3.12. Ele não pode chamar:

- LLM;
- `plan_evidence`;
- workers;
- Retriever;
- Web;
- DuckDB/SQL.

O preflight valida o hash do benchmark, o universo histórico congelado, novidade, cobertura de
capacidades e identidade exata do candidato.

## Gate prospectivo da primeira medição

Para manter comparabilidade com o OH1, os limiares foram definidos antes da primeira execução e
permanecem os mesmos:

- `schema_violations = 0`;
- Evidence Source Set Exact Match médio ≥ 0,65;
- precisão de fontes média ≥ 0,80;
- recall de fontes médio ≥ 0,80;
- DATA tool exact ≥ 0,70;
- DATA arguments exact ≥ 0,60;
- KNOWLEDGE filters joint exact ≥ 0,50;
- WEB parameters exact ≥ 0,70;
- estabilidade modal média ≥ 0,90;
- source-set exact ≥ 0,50 em cada categoria.

A primeira medição deverá usar três repetições com `gpt-4o-mini` e ocorrer **somente depois do
merge deste freeze**. O resultado deverá ser preservado mesmo se algum limiar falhar; falha de
gate não autoriza apagar, repetir seletivamente ou redefinir limiares.

Passar o gate não implica prontidão de produção.
