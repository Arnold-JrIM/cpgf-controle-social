# Gate integral da Governança 1.3.2

## Finalidade

Este gate executa a camada de Governança do Motor 1.3.2 sobre o mesmo snapshot canônico utilizado na regressão integral das Regras 1.2.0. A finalidade é demonstrar que as matrizes diagnósticas e seus resultados estatísticos podem ser reproduzidos de ponta a ponta antes de sua materialização para o dashboard.

O gate não redefine as trilhas nem usa os resultados de redundância para excluir regras. Ele verifica a estabilidade computacional do motor congelado.

## Base canônica

O gate exige exatamente:

- arquivo `CPGF_201301_a_202607.csv`;
- 1.876.087 registros;
- SHA-256 `300789f9bd866f313df4ca5ee5dfca7234050ef2452443b61b1e58425ca0997b`;
- Preparação 1.1.0;
- Regras 1.2.0;
- Motor/Governança 1.3.2.

Qualquer divergência de hash interrompe a execução. Não existe modo de aceitação de outra base neste gate.

## Escopo temporal

Os diagnósticos são congelados para os anos completos de 2013 a 2025. O período de 2026 permanece disponível na base e nas trilhas, mas é excluído das matrizes usadas para congelar sobreposição, marginalidade e diagnósticos multivariados.

Essa decisão evita que julho de 2026 seja tratado como exercício anual completo.

## Invariantes

Antes das assinaturas estatísticas, o gate exige:

- 522.053 unidades `UG × fornecedor × ano` nos anos completos;
- 13.785 unidades `UG × ano` nos anos completos;
- reprodução das contagens de produção T01–T09 já validadas pelo gate anterior.

## Resultados congelados

O relatório registra, sem dados transacionais brutos:

- contagens positivas de T01–T07 e F1–F4 nas respectivas unidades diagnósticas;
- assinatura SHA-256 das duas matrizes binárias;
- Jaccard, Phi e probabilidades condicionais, globalmente e por recortes congelados;
- contribuição marginal, globalmente e por exposição;
- VIF e índices de condição;
- PCA, incluindo componentes, cargas e elegibilidade;
- diagnósticos separados para trilhas e famílias.

T08 e T09 permanecem contextos e não entram no núcleo multivariado.

## Assinaturas e portabilidade numérica

Os resultados determinísticos são normalizados antes do hash:

- ordem determinística das linhas quando aplicável;
- valores flutuantes arredondados para reduzir ruído numérico não substantivo;
- ausências serializadas de forma explícita;
- SHA-256 calculado em streaming, sem persistir as tabelas diagnósticas completas no repositório.

Na validação entre runners, observou-se que 8 das 68 assinaturas derivadas de eigendecomposição podiam variar em detalhes numéricos, embora as matrizes, contagens, sobreposição, marginalidade, elegibilidade e VIF permanecessem idênticos. Como autovetores podem sofrer pequenas variações de sinal, orientação ou arredondamento conforme BLAS/LAPACK e hardware, o contrato portátil diferencia dois níveis de verificação:

1. resultados determinísticos: hash exato;
2. resultados de eigendecomposição: preservação de cardinalidade e esquema, com propriedades matemáticas cobertas pelos testes unitários.

Essa distinção evita falsos negativos de infraestrutura sem reduzir a capacidade do gate de detectar alterações substantivas no motor.

## Fluxo de bootstrap e confirmação

A primeira execução controlada usa `--bootstrap`. Ela deve:

1. validar o hash canônico;
2. reproduzir T01–T09 em produção;
3. reproduzir os dois universos completos;
4. calcular todas as assinaturas;
5. retornar `BOOTSTRAP_PASS`.

Após a inspeção do artefato, o contrato é versionado. A confirmação final é executada contra esse contrato congelado e deve retornar `PASS`.

A confirmação canônica deste gate ocorreu na execução GitHub Actions `31856226920`, commit `774f02a3f40f7eba2c4a0ac8cd06b22b7cc1ab43`, com conclusão `success`. O artefato `governance-regression-report` correspondente possui ID `9239161682` e digest `sha256:d43173ea11415726d8c8f23df9e01f13249888b2b10f0b6013339bf87124befd`.

O workflow pesado permanece disponível apenas por `workflow_dispatch`, evitando recomputações automáticas do snapshot de 522 MB a cada push.

## Limitações

Este gate comprova reprodutibilidade computacional do Motor 1.3.2 sobre o snapshot fixado. Ele não transforma associação em causalidade, não confirma irregularidade e não estabelece que uma trilha com alta sobreposição deva ser removida.
