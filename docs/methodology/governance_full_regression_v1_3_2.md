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

## Assinaturas determinísticas

As tabelas são normalizadas antes da assinatura:

- ordem determinística das linhas quando aplicável;
- normalização de valores flutuantes antes da serialização;
- ausências serializadas de forma explícita;
- SHA-256 calculado em streaming, sem persistir as tabelas diagnósticas completas no repositório.

Para matrizes binárias, sobreposição, marginalidade, elegibilidade, VIF e demais saídas determinísticas, o contrato exige igualdade exata do SHA-256.

## Portabilidade de eigendecomposição

A primeira execução canônica em modo `--bootstrap` retornou `BOOTSTRAP_PASS`. Na passagem estrita subsequente, todos os invariantes, contagens, matrizes e resultados determinísticos foram reproduzidos exatamente, mas 8 das 68 assinaturas diferiram. As oito divergências estavam restritas a tabelas derivadas diretamente de eigendecomposição: componentes, cargas ou índice de condição.

A investigação mostrou que cardinalidade, esquema e universo das tabelas permaneceram idênticos. Esse comportamento é compatível com diferenças numéricas de BLAS/LAPACK e com a não unicidade do sinal ou da base de autovetores em subespaços iguais ou quase degenerados. Nesses casos, exigir identidade byte a byte dos autovetores entre runners distintos seria mais restritivo do que a própria equivalência matemática do diagnóstico.

Por isso, o contrato congelado é deliberadamente portátil:

- mantém SHA-256 exato para todas as saídas determinísticas;
- mantém SHA-256 exato para as matrizes que alimentam os diagnósticos;
- para componentes, cargas e índice de condição derivados de eigendecomposição, congela a presença da tabela, sua cardinalidade e seu esquema;
- mantém testes unitários específicos para fórmulas, orientação determinística, singularidade e propriedades da PCA/VIF.

Essa decisão não aceita uma nova baseline após uma falha. Ao contrário, preserva os resultados determinísticos originalmente observados e explicita qual parte do contrato não pode ser tratada como identidade binária portátil entre bibliotecas numéricas.

O manifesto `data/manifests/governance_regression_1_3_2.json` registra o digest portátil e o diagnóstico que motivou essa distinção.

## Fluxo de validação

A primeira execução controlada usa `--bootstrap`. Ela deve:

1. validar o hash canônico;
2. reproduzir T01–T09 em produção;
3. reproduzir os dois universos completos;
4. calcular todas as assinaturas;
5. retornar `BOOTSTRAP_PASS`.

Após a inspeção do artefato, o contrato portátil é versionado. As execuções seguintes utilizam `--frozen-contract` e somente retornam `PASS` quando:

- o bootstrap interno reproduz todos os checks estruturais;
- o digest do contrato portátil coincide com o manifesto congelado.

O workflow pesado permanece manual após o fechamento do gate, para não baixar e processar aproximadamente 500 MB a cada commit.

## Limitações

Este gate comprova reprodutibilidade computacional do Motor 1.3.2 sobre o snapshot fixado. Ele não transforma associação em causalidade, não confirma irregularidade e não estabelece que uma trilha com alta sobreposição deva ser removida.
