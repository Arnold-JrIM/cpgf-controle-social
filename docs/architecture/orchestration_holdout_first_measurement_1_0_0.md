# Primeira medição independente do Orchestration Holdout 1.0.0

## Status

**Resultado prospectivo: FAIL.**

Este documento preserva a primeira medição independente do `Semantic Evidence Orchestrator 1.0` sobre o `Orchestration Holdout 1.0.0 (OH1)`. O conjunto foi congelado no PR #67 e o harness foi congelado no PR #68 antes de qualquer exposição das 56 perguntas ao candidato.

A execução oficial ocorreu automaticamente após o merge do PR #68, no `main`, sem alteração de prompt, modelo, política do Orchestrator, contratos ou gabaritos entre o freeze e a medição.

## Execução oficial

- workflow: `orchestration-holdout-v1-measurement`;
- run: `32046979526`;
- job `live-measurement`: `95437042301`;
- attempt: `1`;
- evento: `push`;
- commit: `ec87579fe285ddaf29b64bd05e3055ec3cb95736`;
- conclusão: `success`;
- 56 casos × 3 repetições = **168 tentativas LLM**;
- modelo solicitado: `gpt-4o-mini`;
- modelo retornado nas 161 respostas válidas do provider: `gpt-4o-mini-2024-07-18`;
- OpenAI SDK `3.1.0`.

O workflow concluiu com sucesso independentemente do desempenho porque um FAIL faz parte do resultado experimental e deve ser preservado.

## Evidência bruta

Artifact oficial: ID `9293493819`, nome `orchestration-holdout-v1-first-measurement-v1.0.0`, digest ZIP `sha256:9626908d1c5ca5060a9067a85735d770cdc9c85003943b89b9d08f068e150222`.

O JSON original possui `476.264` bytes e SHA-256 `d2213529f505e9d566ab64f1f27aa412e14a348abf997dfdb3d868edbab8c4c5`.

Para preservação permanente, ele foi armazenado como gzip determinístico em `data/evidence/orchestration_holdout_v1_first_measurement_1_0_0.json.gz`, com `33.697` bytes e SHA-256 `ee960b344f5c0cfe796300983bdebd0d1552cf7ee8dc7b7aa400b9573128a54b`. Os testes recompõem o JSON original e verificam ambos os hashes.

## Resultado agregado

- Evidence Source Set Exact Match: **83,93%**;
- precisão média de fontes: **90,48%**;
- recall médio de fontes: **94,35%**;
- ferramenta DATA exata: **93,75%**;
- argumentos DATA exatos: **93,75%**;
- filtros KNOWLEDGE conjuntamente exatos: **0,00%**;
- parâmetros WEB exatos: **53,13%**;
- full-plan exact: **22,62%**;
- estabilidade modal média: **49,40%**;
- violações de schema: **9**;
- falhas de provider: **7**;
- planos inválidos: **2**.

Foram registrados `377.013` tokens de entrada, `33.972` tokens de saída e latência média de aproximadamente `3.172 ms` por tentativa.

## Resultado por categoria

O Source Set Exact Match médio foi `knowledge_only` 100,00%, `knowledge_web` 100,00%, `all_three` 95,83%, `data_only` 91,67%, `data_knowledge` 87,50%, `web_only` 66,67% e `data_web` 45,83%. `data_web` foi a única categoria abaixo do piso prospectivo de 50%.

## Gate prospectivo

Foram satisfeitos **6 de 11** critérios. Passaram três repetições completas, Source Set Exact Match médio, precisão de fontes, recall de fontes, ferramenta DATA e argumentos DATA. Falharam o piso por categoria, filtros KNOWLEDGE, parâmetros WEB, estabilidade modal e zero violações de schema.

Consequentemente, o resultado formal permanece **FAIL no gate prospectivo de generalização ampla**. Os limiares não são reduzidos, arredondados nem reinterpretados após a observação.

## Governança

Este incremento é de preservação, não de tuning. O resultado permite apenas leitura descritiva: a seleção das camadas de evidência foi forte no agregado, mas a primeira medição independente não sustenta generalização ampla do plano estruturado completo.

Após este freeze, o OH1 é material conhecido. Reruns não recuperam independência, o mesmo OH1 não pode sustentar nova alegação independente após tuning e produção permanece desabilitada. As causas dos erros serão analisadas apenas em diagnóstico pós-hoc separado; uma arquitetura alterada a partir desse diagnóstico exigirá novo holdout prospectivamente congelado. O workflow ao vivo é desativado neste freeze para impedir uma segunda execução automática.
