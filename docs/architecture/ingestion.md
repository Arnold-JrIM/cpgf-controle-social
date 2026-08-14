# Ingestão de dados — v0.1

A camada `src/cpgf/ingestion/` separa aquisição, validação e proveniência das transformações analíticas.

## CPGF

Fonte oficial: Portal da Transparência.

Padrão mensal:

```text
https://portaldatransparencia.gov.br/download-de-dados/cpgf/AAAAMM
```

O pipeline:

1. valida a competência `AAAAMM`;
2. baixa para arquivo temporário `.part`;
3. reconhece HTTP 403/429 como bloqueio e HTTP 404 como competência indisponível;
4. exige assinatura ZIP (`PK`);
5. rejeita HTML/CAPTCHA em vez de tentar contornar a proteção;
6. extrai somente o CSV selecionado;
7. preserva os bytes do CSV e apenas padroniza o nome para `AAAAMM_CPGF.csv`;
8. valida as 15 colunas de negócio usadas como referência na baseline;
9. registra SHA-256, tamanho, URL e competência no relatório local.

A atualização incremental começa na competência posterior à última conhecida e encerra no primeiro mês não disponível. Entre downloads há pausa configurável. O manifest canônico versionado no Git não é alterado automaticamente por falha ou bloqueio.

## SIAFI / Unidades Gestoras

Fonte oficial: Tesouro Transparente / CKAN.

O código consulta `package_show`, filtra recursos CSV e seleciona o recurso mais recente segundo `last_modified`/`created`, com tamanho como critério secundário. O arquivo baixado precisa conter, no mínimo, `UG`, `Título` e `UF`.

A seleção dinâmica evita depender de um nome rígido como `siafi_dados_ug_2025.csv`.

## Kaggle

O Kaggle é um snapshot público de reprodução, não a fonte de verdade. O bootstrap usa `kagglehub.dataset_download` e pode baixar o dataset público para `data/raw/kaggle_snapshot/`.

## Comandos

Reprodução rápida:

```bash
python scripts/bootstrap_data.py --source kaggle
```

Reconstrução oficial de uma faixa explícita:

```bash
python scripts/bootstrap_data.py --source official --start 202607 --end 202607
```

Atualização incremental após a baseline:

```bash
python scripts/update_cpgf.py
```

Atualização do cadastro SIAFI:

```bash
python scripts/update_siafi.py
```

Os diretórios `data/raw/` e `data/outputs/` são ignorados pelo Git.
