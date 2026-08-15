# Router Holdout 1.0.0

## Objetivo

O Router Holdout 1.0.0 mede a generalização do Router 1.0.0 para formulações que não participaram do seu ajuste. O conjunto foi criado e congelado antes da primeira execução de avaliação. O roteador não é alterado neste incremento e não existe gate mínimo de acurácia: erros são resultados a preservar, não condições a apagar retroativamente.

O protocolo complementa o Benchmark 1.0.0. O benchmark de desenvolvimento contém 50 perguntas e foi usado para orientar a evolução do roteador no PR #30. Por isso, os 50/50 acertos obtidos naquele conjunto são uma medida in-sample. O holdout busca responder a uma pergunta diferente: até que ponto as regras determinísticas aprendidas no desenvolvimento resistem a novas formulações da mesma classe de intenção?

## Construção do conjunto

O arquivo `data/benchmarks/assistant_router_holdout_v1_0_0.csv` contém 40 perguntas, com oito casos em cada uma das cinco famílias já previstas pelo contrato do benchmark:

- `conceptual_normative`;
- `serving_query`;
- `trail_query`;
- `motor_rule`;
- `safety_interpretation`.

As perguntas usam os mesmos rótulos de rota do contrato existente, mas foram reformuladas com vocabulário e construções sintáticas diferentes das 50 perguntas de desenvolvimento. O conjunto cobre T01–T09, possui IDs próprios (`BENCH-101` a `BENCH-140`) e não contém repetição exata, após normalização, de pergunta do benchmark de desenvolvimento.

O holdout tem SHA-256 `429836fcee9c608478d63df3d69f64aebff4e1219431adf15ea3823b22ad5155`. O benchmark de desenvolvimento permanece congelado com SHA-256 `be1a0245f597f9b2456aacdc6485187d6fdb9c52230f0072519d6387148b5820`.

## Resultado do Router 1.0.0

Na primeira medição, o Router 1.0.0 acertou 19 das 40 rotas, correspondentes a **47,5%** de acurácia no holdout interno.

| Rota esperada | Casos | Acertos | Acurácia |
|---|---:|---:|---:|
| `knowledge` | 8 | 7 | 87,5% |
| `overview` | 4 | 1 | 25,0% |
| `ugs` | 2 | 0 | 0,0% |
| `suppliers` | 2 | 2 | 100,0% |
| `territorial` | 2 | 0 | 0,0% |
| `trails` | 6 | 6 | 100,0% |
| `methodology` | 12 | 2 | 16,7% |
| `composite` | 4 | 1 | 25,0% |

O resultado mostra que a aderência integral ao benchmark de desenvolvimento não se reproduziu nas novas formulações. Em particular, perguntas metodológicas que não usam expressões literais como “como funciona” tendem a cair em `trails`; consultas quantitativas formuladas de modo diferente podem ser capturadas por `knowledge` ou `unsupported`; menções por extenso a “unidades gestoras” não têm a mesma robustez do token `UG`; e a identificação de perguntas `composite` ainda depende de um vocabulário categórico estreito.

Esses padrões são diagnósticos de engenharia, não conclusões substantivas sobre o conteúdo das perguntas. O roteador continua sem LLM, sem execução automática de ferramenta e sem qualquer inferência sobre fraude ou irregularidade.

## Interpretação metodológica

A diferença entre 100% no benchmark de desenvolvimento e 47,5% neste holdout é um sinal de sobreajuste lexical das regras determinísticas ao conjunto usado no desenvolvimento. Essa leitura deve ser feita com cautela. O holdout foi construído internamente no mesmo projeto, não por avaliadores externos independentes, e contém apenas 40 casos. Portanto, ele é mais forte que a métrica in-sample para revelar fragilidades de generalização, mas não constitui estimativa de acurácia de produção.

O valor metodológico do resultado está em preservar a separação entre desenvolvimento e avaliação. O Router 1.0.0 não será modificado neste PR depois de observados os erros. O conjunto poderá ser usado posteriormente como regressão, mas deixará de ser “não visto” para qualquer versão do roteador ajustada com base nesses erros.

## Consequência para a próxima versão

Uma futura versão Router 1.1.0 poderá tratar as fragilidades identificadas, preferencialmente por regras de intenção mais estruturais e menos dependentes de palavras exatas, além de rever a precedência entre consultas analíticas, Knowledge e fallback de trilhas. Contudo, qualquer ajuste baseado neste holdout exigirá **um novo conjunto não visto** para nova alegação de generalização.

O próximo incremento não deve alterar retrospectivamente este arquivo, seu hash, os rótulos do holdout ou o resultado do Router 1.0.0.

## Evidência reproduzível

A execução funcional foi realizada no commit `a00c2975e80751c1f808cf12ab7d8d133755cb67`, workflow run `31907563260`, com conclusão `success`. O artefato `router-holdout-v1.0.0-evaluation` recebeu ID `9252766871` e digest `sha256:db1055e51a832cd9a7bf0e388f50db7030627a0d18641fc0439f7fd594e5f27d`.
