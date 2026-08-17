# Orchestration Holdout 1.0.0

## Objetivo

Este artefato congela a primeira avaliação prospectiva do **Semantic Evidence Orchestrator 1.0** antes de qualquer execução do `gpt-4o-mini` sobre as perguntas do conjunto.

O holdout avalia a capacidade de transformar uma pergunta em um conjunto mínimo e executável de necessidades de evidência. Ele não mede, neste PR, a qualidade dos workers, do Retriever, da busca web, da síntese ou da resposta final.

## Cobertura combinatória

São **56 casos**, oito para cada um dos sete conjuntos não vazios possíveis entre as três fontes governadas:

- `DATA`;
- `KNOWLEDGE`;
- `WEB`;
- `DATA + KNOWLEDGE`;
- `KNOWLEDGE + WEB`;
- `DATA + WEB`;
- `DATA + KNOWLEDGE + WEB`.

Assim, `DATA`, `KNOWLEDGE` e `WEB` aparecem em 32 casos cada. A inclusão de `DATA + WEB` completa a cobertura combinatória das três fontes e evita avaliar apenas combinações previamente enfatizadas pelo diagnóstico do JH5.

## Oráculos

Cada caso congela antes da primeira medição:

- conjunto esperado de fontes;
- ferramenta DATA esperada, quando aplicável;
- argumentos DATA já normalizados pelos contratos reais;
- scopes, temporalidades e classes de fonte de KNOWLEDGE;
- parâmetros WEB.

Os casos WEB usam somente pesquisa oficial (`official_only=true`) e sempre trazem janela explícita de freshness. Isso reduz ambiguidade do oráculo e testa a fronteira criada no PR #64.

## Artefato

O benchmark é versionado em:

`data/benchmarks/orchestration_holdout_v1_0_0.csv.gz`

A compactação é determinística e o manifesto fixa tanto o hash do arquivo comprimido quanto o hash do CSV descomprimido. A compactação não oculta o conteúdo; ela apenas reduz o tamanho do snapshot versionado.

## Independência

O Orchestrator 1.0 foi congelado no `main` após o merge do PR #66, antes da autoria deste holdout. O manifesto fixa:

- versão e política do Orchestrator;
- `gpt-4o-mini`;
- OpenAI SDK;
- contrato de evidência;
- blobs Git do Orchestrator, política de modelo, workers, registry e política WEB.

O preflight **não importa nem chama `plan_evidence()`** e não executa provider LLM. Também não aciona worker DATA, Retriever, busca web ou SQL.

JH4 e JH5 continuam conhecidos. Eles entram apenas no universo histórico usado para rejeitar repetição de perguntas; suas saídas não são usadas para produzir o gabarito do novo conjunto.

## Novidade textual

Antes da medição, o preflight compara as 56 perguntas com todos os benchmarks CSV anteriores que possuam coluna `question`.

O gate prospectivo exige:

- zero repetição exata após normalização;
- similaridade máxima de sequência <= 0,70;
- universo histórico esperado de 9 benchmarks e 374 perguntas.

Se uma pergunta violar esse gate, ela pode ser reescrita **somente antes da primeira medição**, pois ainda não terá recebido saída da candidata.

## Gate prospectivo

A primeira medição será executada em PR separado, com três repetições por caso. Antes dela ficam congelados:

- Evidence Source Set Exact Match médio >= 0,65;
- precisão média de fontes >= 0,80;
- recall médio de fontes >= 0,80;
- seleção exata da ferramenta DATA >= 0,70;
- argumentos DATA exatos >= 0,60;
- filtros KNOWLEDGE conjuntamente exatos >= 0,50;
- parâmetros WEB exatos >= 0,70;
- estabilidade modal média >= 0,90;
- Source Set Exact Match >= 0,50 em cada uma das sete categorias;
- zero violação de schema.

Os limiares são regras de governança do projeto, não testes de significância. Uma primeira medição abaixo do gate deve ser preservada e reportada, e não apagada por falha do workflow.

## Sequência experimental

1. **PR #67**: congelar benchmark, oráculos, hashes, candidata e gate; nenhum LLM é executado.
2. **PR #68**: executar a primeira medição independente com `gpt-4o-mini`, preservar saídas brutas, hashes, metadados e métricas.
3. Somente após a preservação do resultado, decidir se há justificativa para tuning. Se houver alteração do Orchestrator com base no OH1, este conjunto passa a ser conhecido e uma nova avaliação independente será necessária para nova alegação de generalização.
