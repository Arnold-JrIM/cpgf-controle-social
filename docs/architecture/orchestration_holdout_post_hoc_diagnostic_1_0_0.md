# Orchestration Holdout 1.0.0 — diagnóstico pós-hoc

Status: **POST_HOC_DIAGNOSTIC_ONLY**  
Versão: **1.0.0**

## Objetivo

Este incremento diagnostica a primeira medição independente do `Semantic Evidence Orchestrator 1.0` sobre o OH1 depois de o resultado oficial ter sido congelado. O objetivo é localizar os mecanismos de erro antes de qualquer alteração de prompt, política, contrato ou arquitetura.

O OH1 já é material conhecido. Consequentemente, qualquer ajuste motivado por este diagnóstico não poderá ser reavaliado no próprio OH1 como nova evidência independente.

## Fonte de evidência

O diagnóstico utiliza exclusivamente a evidência bruta congelada pelo PR #69. O loader recompõe as oito partes base64, valida o SHA-256 da concatenação, decodifica o gzip, valida o SHA-256 do gzip e, por fim, valida o SHA-256 do JSON original antes de ler qualquer linha de avaliação.

Nenhum LLM, worker, Retriever, busca Web, DuckDB ou SQL é executado.

## Dimensões diagnósticas

A análise decompõe as 168 execuções em seis blocos:

1. **Seleção de fontes** — matriz entre conjuntos esperados e previstos, under-routing, over-routing e desempenho por categoria.
2. **DATA** — ferramenta, argumentos e mismatches por parâmetro.
3. **KNOWLEDGE** — separação entre `scopes`, `temporal_statuses` e `source_classes`, permitindo identificar qual dimensão impede o joint exact.
4. **WEB** — exact match conjunto e mismatches por chave/valor dos parâmetros.
5. **Estabilidade** — modal share por caso para fontes, ferramenta DATA, parâmetros DATA, filtros KNOWLEDGE, parâmetros WEB e assinatura completa.
6. **Falhas estruturais/provider** — schema violations, falhas do provider e planos inválidos localizados por caso e repetição.

## Achados observados

A seleção do conjunto de evidências é substancialmente mais forte do que o plano completo. Das 168 execuções, 141 acertaram exatamente o conjunto de fontes, enquanto somente 38 produziram um plano integralmente exato. Houve 10 linhas com under-routing e 18 com over-routing. Todas as fontes adicionais indevidas foram `KNOWLEDGE`, o que localiza uma tendência específica de expansão semântica.

Essa tendência aparece com maior clareza em `DATA+WEB`. Apenas 11 das 24 execuções da categoria acertaram exatamente o conjunto de fontes, e 12 foram transformadas em `DATA+KNOWLEDGE+WEB`. Em `WEB-only`, outras cinco execuções acrescentaram `KNOWLEDGE`. Assim, a principal deficiência de seleção de fonte não é uma incapacidade geral de reconhecer consultas compostas, mas a inclusão excessiva de evidência documental em consultas que pediam apenas dados e informação externa atual.

O componente DATA apresentou comportamento forte e estável. Das 96 execuções em que DATA era obrigatório, 90 acertaram a ferramenta e 90 acertaram conjuntamente os argumentos. Os parâmetros `metric` e `reference` tiveram exact match integral, e os demais ficaram próximos de 90% ou acima. As perdas se concentram sobretudo nas linhas que também apresentaram falha estrutural ou ausência de plano válido.

O principal gargalo é a parametrização de KNOWLEDGE. Embora `knowledge_only` e `knowledge_web` tenham acertado o conjunto de fontes nas 24 execuções de cada categoria, nenhuma das 96 linhas que exigiam KNOWLEDGE acertou conjuntamente `scopes`, `temporal_statuses` e `source_classes`. Os exact matches isolados foram 11,46% para `scopes`, 10,42% para `temporal_statuses` e 23,96% para `source_classes`. O padrão dominante é de **superexpansão de filtros**. Por exemplo, `cpgf_core` foi frequentemente ampliado para `control_external+cpgf_core+methodology`, enquanto `contextual` foi previsto 37 vezes como `current+historical`. Também houve adição recorrente de classes `normative` e `institutional` quando o gabarito exigia um conjunto mais restrito.

No componente WEB, 51 das 96 execuções tiveram parâmetros conjuntamente exatos. O parâmetro `limit` permaneceu forte, com 93,75% de exact match, enquanto `official_only` alcançou 67,71% e `max_age_days`, 58,33%. O erro mais frequente em `official_only` foi prever `false` quando o esperado era `true`, em 26 execuções. Em `max_age_days`, os valores temporais foram repetidamente convertidos em `null`, sobretudo para janelas esperadas de 30, 60 e 90 dias.

A instabilidade também se localiza principalmente depois da escolha da fonte. O modal share médio foi 94,64% para status, 90,48% para fontes, 96,43% para ferramenta DATA e 96,43% para argumentos DATA. Caiu para 83,93% nos parâmetros WEB, 55,95% nos filtros KNOWLEDGE e 49,40% na assinatura completa. Portanto, a baixa estabilidade agregada não decorre de uma rota semântica globalmente errática; ela é amplificada sobretudo pela parametrização documental.

As nove violações de schema formam um canal de falha separado. Sete foram `ORCHESTRATOR_PROVIDER_FAILED:ValidationError` e duas `ORCHESTRATOR_PLAN_INVALID:ValidationError`. Como essas falhas são de contrato/validação, tratá-las apenas por tuning semântico misturaria causas distintas e dificultaria a atribuição de melhoria.

## Leitura arquitetural

Os achados favorecem uma intervenção em camadas. A primeira prioridade deve ser tornar determinísticos os aspectos que já possuem semântica normativa no contrato: canonicalização de filtros, validação de combinações permitidas, defaults governados de WEB e tratamento mais robusto da saída estruturada do provider. A segunda prioridade é restringir a inclusão de `KNOWLEDGE` quando a pergunta não contém necessidade normativa, metodológica ou documental observável. Somente depois dessas correções deve-se avaliar se permanece um erro residual que justifique alteração do prompt.

Essa leitura é pós-hoc e não constitui evidência independente de que a intervenção proposta melhorará a generalização. O OH1 serve daqui em diante apenas como material de desenvolvimento e diagnóstico.

## Invariantes de governança

- OH1 permanece conhecido e não volta a ser holdout independente.
- O diagnóstico é totalmente offline e determinístico.
- Não há tuning de prompt ou política neste PR.
- Não há alteração no `Semantic Evidence Orchestrator 1.0`.
- Não há ativação de produção.
- O gate prospectivo original permanece FAIL; nenhum threshold é relaxado ou reinterpretado.
- Qualquer arquitetura alterada após o diagnóstico exigirá novo holdout prospectivamente congelado para sustentar nova alegação de generalização.

## Critério para o próximo incremento

O próximo incremento deve implementar a menor intervenção compatível com os padrões observados, separando correções determinísticas de contrato/normalização de eventuais mudanças semânticas de prompt. Depois da alteração, uma nova alegação de generalização exigirá um holdout prospectivo diferente do OH1.
