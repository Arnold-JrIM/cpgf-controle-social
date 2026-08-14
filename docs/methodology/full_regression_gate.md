# Gate de regressão integral T01–T09

Esta etapa é executada **depois** do port das nove trilhas para `src/`. Seu objetivo é separar duas afirmações que não devem ser confundidas:

1. o código possui testes unitários e de integração que passam no CI;
2. o novo pipeline reproduz, sobre o mesmo arquivo congelado, as contagens obtidas na baseline histórica.

Somente a segunda afirmação é tratada por este gate.

## Entrada canônica

O gate espera o arquivo consolidado:

- `CPGF_201301_a_202607.csv`;
- SHA-256 `300789f9bd866f313df4ca5ee5dfca7234050ef2452443b61b1e58425ca0997b`.

O hash é validado **antes** da leitura integral do CSV. Uma divergência interrompe a execução por padrão. A opção `--allow-other-hash` existe apenas para diagnóstico explícito e marca o relatório como `DIAGNOSTIC_ONLY`; ela não valida a baseline.

O CSV não deve ser versionado no GitHub. O projeto mantém no repositório apenas código, contrato, manifests, fixtures e resultados pequenos necessários à reprodutibilidade.

## Modos de identidade do portador

A mesma camada de staging contém duas identidades:

- `PORTADOR_ID_BASELINE`: semântica histórica da Preparação 1.0.0;
- `PORTADOR_ID`: identidade composta da Preparação 1.1.0.

As trilhas T03, T04, T05 e T07 são reexecutadas nos dois modos. T01, T02, T06, T08 e T09 não dependem da identidade do portador e são calculadas uma única vez por execução.

Isso permite preservar simultaneamente a reprodutibilidade histórica e a baseline de produção. A diferença conhecida permanece restrita à T07:

| Trilha | Preparação 1.0.0 | Preparação 1.1.0 |
|---|---:|---:|
| T07 | 1.089 | 1.088 |

T03, T04 e T05 devem permanecer numericamente invariantes entre as duas identidades no arquivo congelado.

## Contagens esperadas

O gate não mantém uma segunda cópia manual do contrato. As expectativas são lidas de `config/trails.yaml`:

| Trilha | Baseline histórica |
|---|---:|
| T01 | 49.675 |
| T02 | 14 |
| T03 | 7.534 |
| T04 | 1.384 |
| T05 | 1.693 |
| T06 | 233 |
| T07 | 1.089 |
| T08 | 12 |
| T09 | 46.941 |

No modo de produção, a expectativa de T07 é substituída por 1.088; as demais permanecem iguais.

Esses números representam unidades próprias de cada trilha e **não** devem ser somados como se todos fossem alertas homogêneos. T01 e T09, em particular, possuem papel contextual/observacional de alta frequência.

## Execução

A forma explícita é:

```bash
python scripts/run_full_regression.py \
  --input data/raw/CPGF_201301_a_202607.csv \
  --mode both
```

O relatório padrão é gravado em:

```text
data/outputs/full_regression_report.json
```

Para cada trilha, o JSON registra valor esperado, valor obtido, diferença e resultado do check, além do tempo aproximado de execução. O relatório não contém linhas transacionais nem identificadores pessoais.

## Critério de aprovação

O status `PASS` requer simultaneamente:

- SHA-256 canônico;
- igualdade exata das nove contagens no modo histórico solicitado;
- igualdade exata das nove contagens no modo de produção solicitado.

Qualquer diferença produz `FAIL` e o script encerra com código diferente de zero. Isso obriga a investigação da divergência em vez de ajustar silenciosamente a expectativa.

O status `DIAGNOSTIC_ONLY` é reservado a arquivos não canônicos executados com autorização explícita. Mesmo que as contagens coincidam, esse status não é evidência de reprodução da baseline.

## Relação com o CI

O workflow normal do GitHub Actions continua usando fixtures pequenas para lint e testes automatizados. Ele **não** baixa automaticamente o CSV histórico de aproximadamente meio gigabyte e não substitui a regressão integral.

Essa separação reduz custo e fragilidade no CI e deixa claro que a validação científica/reprodutiva do motor depende de uma execução controlada sobre a base congelada.
