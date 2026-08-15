# Knowledge 1.1.0 — corpus local governado

O Git versiona **catálogo, contratos, manifestos e código**, não o acervo original de PDFs.

## Preparação local

Extraia a coleção documental autorizada em:

`data/knowledge/sources/`

preservando a estrutura de diretórios usada pelo catálogo, por exemplo:

- `Artigos Open Acess/`;
- `Normas Oficiais/`;
- `Publicações Públicas/`;
- referências metodológicas na raiz.

Os caminhos e, quando congelados, SHA-256, tamanho e número de páginas esperados ficam nos arquivos de `data/knowledge/catalog/`. O arquivo `source_catalog.json` funciona como índice versionado desses catálogos.

O diretório `sources/` permanece ignorado pelo Git.

## Build

Não converta PDFs manualmente para JSON, TXT ou Parquet. Execute:

```bash
python scripts/build_knowledge.py
```

O pipeline extrai o texto disponível, preserva página, normaliza, cria chunks determinísticos e gera localmente:

- `data/knowledge/processed/documents.parquet`;
- `data/knowledge/processed/chunks.parquet`;
- `data/knowledge/processed/knowledge_manifest.json`.

Para conferir uma coleção local completa:

```bash
python scripts/build_knowledge.py --require-all-sources --require-text-sources
```

`--require-all-sources` exige as fontes que possuem caminho local previsto. Fontes deliberadamente metadata-only, como uma referência atual ainda não materializada, não são consideradas ausentes. `--require-text-sources` exige texto extraível apenas das fontes habilitadas para recuperação padrão.

## Governança de recuperação

Cada documento possui:

- `scope`: `cpgf_core`, `control_external`, `methodology`, `historical`, `institutional_mb` ou `discovery`;
- `temporal_status`: `current`, `historical` ou `contextual`;
- `retrieval_default`: inclusão ou exclusão da recuperação ordinária;
- `supports_trails`: fundamento direto explicitamente curado para T01–T09;
- `related_trails`: pertinência metodológica ou contextual, sem afirmar fundamento direto;
- `distribution_policy`: política de distribuição independente do fato de o documento ter sido obtido legalmente.

Fontes históricas, materiais específicos da MB, obras integrais de descoberta e outros conteúdos com `retrieval_default=false` somente entram mediante opt-in explícito.

## Política de distribuição

`public_official` identifica fonte oficial pública; `open_license` registra licença aberta; `metadata_only` significa que o projeto não presume autorização para redistribuir o PDF ou seus chunks; `project_owned` identifica material produzido/controlado pelo projeto.

Uma futura distribuição pública do Knowledge deverá respeitar essas políticas por documento. Embeddings, índice vetorial, busca web, upload de arquivos pelo usuário e chamada a LLM permanecem fora do Knowledge 1.1.0.
