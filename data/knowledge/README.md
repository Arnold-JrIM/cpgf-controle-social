# Knowledge 1.0.0 — fontes locais

O Git versiona **metadados, contratos e código**, não o acervo original de PDFs.

Coloque cópias locais autorizadas dos documentos em:

`data/knowledge/sources/`

Os nomes esperados estão em `source_catalog.json`. O diretório `sources/` é ignorado pelo Git.

Execute:

```bash
python scripts/build_knowledge.py
```

O build gera localmente:

- `data/knowledge/processed/documents.parquet`;
- `data/knowledge/processed/chunks.parquet`;
- `data/knowledge/processed/knowledge_manifest.json`.

Use `--require-all-sources` somente quando quiser exigir que todos os documentos ativos estejam presentes.

## Política de distribuição

`public_official` identifica fonte oficial pública; `open_license` exige registro da licença; `metadata_only` significa que o projeto **não presume autorização para redistribuir o PDF ou seus chunks**. O processamento local continua possível para fins autorizados, mas uma futura release do Knowledge deverá aplicar uma política específica de exclusão ou revisão de conteúdo conforme a licença de cada documento.
