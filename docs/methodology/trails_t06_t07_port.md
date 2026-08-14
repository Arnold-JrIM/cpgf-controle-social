# Portabilidade T06–T07 — Regras 1.2.0

## Escopo

Este documento registra a migração para `src/` de T06 (concentração em fornecedor) e T07 (recorrência de múltiplos saques), sem recalibrar os critérios congelados das Regras 1.2.0.

As saídas são sinais analíticos para triagem. Concentração não demonstra favorecimento, e recorrência de saques não demonstra uso indevido. A interpretação depende de contexto e, quando aplicável, documentação não presente na base pública.

## T06 — concentração em fornecedor

A unidade é `UG × ANO_TRANSACAO`. A população é formada por compras nacionais com valor positivo e UG/ano observáveis. O sinal exige simultaneamente:

- pelo menos 20 compras com fornecedor identificado;
- pelo menos 3 fornecedores identificados;
- cobertura de valor identificado de pelo menos 80%;
- participação do maior fornecedor por valor de pelo menos 50%.

A triagem permanece: `ATENCAO` de 50% a <70%, `REFORCADO` de 70% a <80% e `MUITO_ELEVADO` a partir de 80%. Também são calculados Top-5, HHI e concentração por quantidade. A ponte de rastreabilidade relaciona o sinal às compras do fornecedor Top-1 por valor.

A baseline congelada da Preparação 1.0.0 contém 233 UG-anos sinalizados.

## T07 — recorrência de múltiplos saques

T07 mantém duas camadas. T07-A é descritiva e identifica episódios `UG × portador × dia` com pelo menos dois saques efetivos. Episódios com 3 ou mais saques recebem nível `REFORCADO`; os demais, `ATENCAO`.

T07-B resume, por `UG × portador × ANO_TRANSACAO`, o número de dias com múltiplos saques. A priorização exige:

- pelo menos 3 dias com múltiplos saques;
- pelo menos 10 portadores comparáveis no exercício;
- `N_DIAS_MULTISAQUE` maior ou igual ao P90 anual, preservando empates no limiar.

O percentil é relativo ao exercício e não constitui score jurídico ou probabilidade de irregularidade.

## Identidade do portador e regressão

A baseline histórica usa Preparação 1.0.0 e `PORTADOR_ID_BASELINE`; por isso, a contagem congelada permanece T07 = 1.089. A Preparação 1.1.0 usa a chave composta `UG + CPF mascarado + nome normalizado`. O gate de identidade demonstrou que os 22.609 episódios diários permanecem iguais, mas um agrupamento anual de 2022 é desfeito, produzindo expectativa de T07 = 1.088 na preparação de produção.

Essa diferença é versionada e intencional. Não se altera retroativamente a baseline de regressão das Regras 1.2.0.

## Testes

O CI usa fixtures pequenas e determinísticas. Os testes verificam os limiares de T06, o P90 e o mínimo de comparáveis de T07 e a possibilidade de reexecutar explicitamente a identidade histórica do portador. A regressão integral sobre `CPGF_201301_a_202607.csv` permanece uma etapa controlada e separada do CI ordinário.
