# Camada de serving 1.4.0 — Parquet e DuckDB

## Finalidade

A camada de serving materializa os resultados já validados da Preparação 1.1.0, das Regras 1.2.0 e do Motor/Governança 1.3.2 em artefatos próprios para consulta pelo dashboard e, futuramente, pelas ferramentas de IA.

O objetivo é impedir que o Streamlit recalcule trilhas e diagnósticos a cada acesso. A aplicação passa a consultar uma camada curada, versionada e verificável.

## Fonte canônica

Para publicação, `scripts/build_serving.py` exige o snapshot canônico:

- `CPGF_201301_a_202607.csv`;
- 1.876.087 registros;
- SHA-256 congelado no manifesto da Governança 1.3.2.

O modo `--allow-noncanonical` existe apenas para desenvolvimento e testes e não deve ser usado para gerar artefatos publicados.

## Artefatos

O bundle padrão é gravado em `data/processed/serving/`, diretório ignorado pelo Git.

Ele contém:

- `parquet/matrix_supplier_year.parquet`;
- `parquet/matrix_ug_year.parquet`;
- Parquets dos diagnósticos de sobreposição, marginalidade, VIF, índice/número de condição e PCA;
- `serving_manifest.json`;
- `cpgf_serving.duckdb`.

As matrizes completas preservam o período parcial de 2026 com seu `STATUS_PERIODO`. Os diagnósticos estatísticos continuam restritos a exercícios completos de 2013 a 2025, em conformidade com o gate integral do PR #19.

## Contrato com a Governança 1.3.2

Antes de publicar um bundle canônico, a materialização verifica:

1. SHA-256 do CSV de origem;
2. 522.053 unidades `UG × fornecedor × ano` nos exercícios completos;
3. 13.785 unidades `UG × ano` nos exercícios completos;
4. assinatura determinística das duas matrizes contra o manifesto congelado do PR #19.

Assim, a camada de serving não cria uma nova interpretação das trilhas. Ela apenas materializa resultados que já passaram pela regressão integral.

## Manifesto do bundle

Cada Parquet recebe metadados com:

- nome lógico;
- classe (`matrix` ou `diagnostic`);
- caminho relativo;
- número de registros;
- lista ordenada de colunas;
- SHA-256 do arquivo;
- tamanho em bytes.

O manifesto também registra as versões de preparação, regras, motor e serving, além da proveniência do input e do resultado da validação canônica.

O contrato de proveniência em `data/manifests/serving_1_4_0_contract.json` foi congelado a partir do primeiro build canônico aprovado. A execução `31857600533`, no commit `c9cceef5d645ce26ef833542c1e884b31f6f1a33`, concluiu com sucesso e gerou o artefato `serving-manifest-1.4.0` (ID `9239587655`, digest `sha256:7331a5c3252107e929cee452b016b443c76e1d2f250ea8ba7f4b429a96cf12f7`).

## DuckDB

O catálogo DuckDB é autocontido. Para cada Parquet é criada:

- uma tabela física `srv_<nome_logico>`;
- uma view autorizada `v_<nome_logico>`.

A duplicação é deliberada: os Parquets permanecem como formato de intercâmbio/reprodução e o DuckDB oferece uma unidade de consulta portátil, sem depender de caminhos absolutos para arquivos externos.

A tabela `serving_catalog` mantém o mapeamento entre nomes lógicos, tabelas, views, caminhos e hashes.

## Segurança de consulta

`ServingRepository` não recebe nomes SQL arbitrários. Ele aceita apenas nomes lógicos validados e consulta somente views registradas no `serving_catalog`.

Nesta etapa não há ferramenta de SQL livre para o LLM. A restrição de SQL gerado por IA a `SELECT`, limites de recursos e demais guardrails continuam reservados à etapa de integração do assistente.

## Integridade

`validate_serving_bundle()` verifica:

- existência de cada Parquet;
- hash do arquivo;
- cardinalidade;
- ordem/schema das colunas;
- existência e hash do catálogo DuckDB;
- correspondência entre o número de tabelas do manifesto e do catálogo.

Qualquer divergência retorna `FAIL`.

## Execução

```bash
python scripts/build_serving.py \
  --input data/raw/CPGF_201301_a_202607.csv \
  --output-dir data/processed/serving
```

Para um fixture ou desenvolvimento local:

```bash
python scripts/build_serving.py \
  --input caminho/fixture.csv \
  --output-dir tmp/serving \
  --allow-noncanonical
```

O workflow pesado `.github/workflows/serving_build_canonical.yml` permanece disponível apenas por `workflow_dispatch`, evitando recomputação do snapshot integral a cada `push` ou Pull Request.

## Limites desta etapa

O serving 1.4.0 não altera T01–T09, não cria score, não reclassifica alertas e não implementa a experiência visual do dashboard. A integração do Streamlit deverá consumir esta camada em PR posterior.
