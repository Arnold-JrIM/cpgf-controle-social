# Smoke test real da ingestão

## Objetivo

Os testes unitários do projeto não dependem de rede. O smoke test complementa o CI ao verificar, de forma controlada, se a implementação conversa com as fontes externas reais.

Ele não substitui os testes unitários nem a regressão metodológica.

## Fontes verificadas

### CPGF / Portal da Transparência

O teste faz apenas uma sondagem em streaming e lê o primeiro bloco da resposta. Não baixa integralmente o ZIP.

São consultadas:

1. a última competência congelada no manifest `data/manifests/cpgf.json`;
2. a competência imediatamente seguinte.

Resultados reconhecidos:

- `ZIP_AVAILABLE`: a fonte retornou conteúdo com assinatura ZIP;
- `NOT_AVAILABLE`: usado apenas como resultado esperado possível para a competência seguinte;
- `BLOCKED`: HTTP 403/429; a proteção do Portal foi detectada e respeitada;
- `HTML_PROTECTION`: a resposta aparenta ser HTML/CAPTCHA/validação humana.

Para a competência da baseline, `NOT_AVAILABLE` é falha, porque ela já é conhecida no snapshot congelado. `BLOCKED` e `HTML_PROTECTION` resultam em `PASS_WITH_PORTAL_PROTECTION`: o acesso ao conteúdo não foi confirmado, mas o fail-safe operou conforme o contrato.

### SIAFI / Tesouro Transparente

O teste consulta o `package_show` do CKAN, descobre o CSV mais recente, baixa o recurso e valida as colunas mínimas `UG`, `Título` e `UF`.

O download é pequeno o suficiente para um smoke test e registra recurso, data de modificação, tamanho, SHA-256 e schema no relatório.

### Kaggle

Para não baixar o consolidado CPGF de centenas de MB, o teste solicita somente `siafi_dados_ug_2025.csv` do dataset público `arnoldjrim/dados-abertos-cpgf-2013-a-2026`.

O arquivo precisa existir e satisfazer o schema mínimo do cadastro de UGs.

## Execução local

```bash
python scripts/smoke_ingestion.py
```

O relatório é gravado em:

```text
data/outputs/smoke/ingestion_smoke.json
```

Esse diretório é ignorado pelo Git.

## GitHub Actions

O workflow `ingestion-smoke` roda automaticamente apenas no branch `test/ingestion-smoke`. Depois que o workflow for incorporado à `main`, ele ficará disponível também para execução manual por `workflow_dispatch`.

O relatório JSON é enviado como artifact por 14 dias.

## Critério de aceite

- `PASS`: três superfícies externas responderam conforme esperado;
- `PASS_WITH_PORTAL_PROTECTION`: SIAFI e Kaggle passaram, e o Portal respondeu com proteção reconhecida;
- `FAIL`: SIAFI/Kaggle falharam, a competência conhecida do CPGF apareceu como indisponível, ou houve resposta externa não reconhecida.

Nenhum arquivo bruto baixado pelo smoke test é versionado no Git.
