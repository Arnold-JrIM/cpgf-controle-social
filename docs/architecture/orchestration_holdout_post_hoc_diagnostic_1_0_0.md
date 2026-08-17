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

## Invariantes de governança

- OH1 permanece conhecido e não volta a ser holdout independente.
- O diagnóstico é totalmente offline e determinístico.
- Não há tuning de prompt ou política neste PR.
- Não há alteração no `Semantic Evidence Orchestrator 1.0`.
- Não há ativação de produção.
- O gate prospectivo original permanece FAIL; nenhum threshold é relaxado ou reinterpretado.
- Qualquer arquitetura alterada após o diagnóstico exigirá novo holdout prospectivamente congelado para sustentar nova alegação de generalização.

## Critério para o próximo incremento

O próximo PR somente poderá alterar o Orchestrator depois que este diagnóstico separar, com evidência observada, problemas de reconhecimento das fontes de problemas de parametrização, instabilidade e falhas estruturais. A correção escolhida deverá ser a menor intervenção compatível com os padrões observados.
