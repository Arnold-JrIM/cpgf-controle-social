# Resultado da regressão integral T01–T09 — 2026-08-14

A regressão integral foi executada sobre o arquivo canônico `CPGF_201301_a_202607.csv`, com 1.876.087 registros de dados e SHA-256 `300789f9bd866f313df4ca5ee5dfca7234050ef2452443b61b1e58425ca0997b`.

O gate retornou `PASS` tanto para a baseline histórica quanto para a preparação de produção.

## Baseline histórica — Preparação 1.0.0

- T01 = 49.675
- T02 = 14
- T03 = 7.534
- T04 = 1.384
- T05 = 1.693
- T06 = 233
- T07 = 1.089
- T08 = 12
- T09 = 46.941

Todas as contagens reproduziram exatamente o contrato congelado das Regras 1.2.0, com delta zero.

## Produção — Preparação 1.1.0

- T01 = 49.675
- T02 = 14
- T03 = 7.534
- T04 = 1.384
- T05 = 1.693
- T06 = 233
- T07 = 1.088
- T08 = 12
- T09 = 46.941

A única diferença em relação à baseline histórica é T07, já prevista e documentada no gate de identidade do portador. A Preparação 1.1.0 separa uma colisão histórica da chave mascarada de CPF dentro da mesma UG. Esse efeito reduz em uma unidade a priorização T07 de produção, sem alterar os critérios da trilha e sem reescrever retroativamente a baseline 1.0.0.

## Interpretação

O resultado valida a reprodução executável das nove trilhas para o arquivo canônico sob as versões `Regras 1.2.0` e `Motor 1.3.2`, distinguindo explicitamente a preparação histórica 1.0.0 da preparação de produção 1.1.0.

O `PASS` é uma validação de regressão computacional do motor. Ele não converte sinais em conclusões de fraude ou irregularidade e não elimina as limitações de observabilidade, aplicabilidade normativa ou necessidade de exame contextual já registradas na documentação metodológica.

O manifesto correspondente está em `data/manifests/full_regression_20260814.json` e não contém registros transacionais brutos.
