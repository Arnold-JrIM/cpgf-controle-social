# Knowledge 1.2.0 — corpus local governado e recuperação híbrida

O Git versiona **catálogo, contratos, manifestos e código**, não o acervo original de PDFs nem os artefatos vetoriais gerados localmente.

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

## Build documental

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

## Índice semântico local

O Knowledge 1.2.0 mantém a recuperação lexical como baseline e acrescenta recuperação semântica e híbrida. O índice vetorial é um artefato local opcional e não é criado durante o build documental comum.

Com `OPENAI_API_KEY` configurada no ambiente, a construção explícita do índice pode ser feita por:

```bash
python scripts/build_semantic_index.py \
  --bundle-dir data/knowledge/processed
```

O padrão do provider é `text-embedding-3-small`, com 768 dimensões. A CLI gera e valida:

- `data/knowledge/processed/embeddings.parquet`;
- `data/knowledge/processed/embeddings_manifest.json`.

O manifesto do índice liga os embeddings ao SHA-256 exato de `chunks.parquet`. Um índice construído para outro corpus, com cobertura incompleta, dimensionalidade divergente ou hash alterado é rejeitado por `validate_semantic_index()`.

Nenhuma chamada externa de embeddings ocorre no CI comum ou no smoke padrão. A geração do índice real é **opt-in** e pressupõe decisão explícita do responsável pelo projeto sobre o uso de provedor externo.

## Governança de recuperação

Cada documento possui:

- `scope`: `cpgf_core`, `control_external`, `methodology`, `historical`, `institutional_mb` ou `discovery`;
- `temporal_status`: `current`, `historical` ou `contextual`;
- `retrieval_default`: inclusão ou exclusão da recuperação ordinária;
- `supports_trails`: fundamento direto explicitamente curado para T01–T09;
- `related_trails`: pertinência metodológica ou contextual, sem afirmar fundamento direto;
- `distribution_policy`: política de distribuição independente do fato de o documento ter sido obtido legalmente.

Os mesmos filtros governam a recuperação lexical e semântica. Fontes históricas, materiais específicos da MB, obras integrais de descoberta e outros conteúdos com `retrieval_default=false` somente entram mediante opt-in explícito.

A recuperação híbrida usa Reciprocal Rank Fusion (RRF) para combinar os rankings lexical e semântico sem somar diretamente scores de escalas distintas.

## Política de distribuição

`public_official` identifica fonte oficial pública; `open_license` registra licença aberta; `metadata_only` significa que o projeto não presume autorização para redistribuir o PDF ou seus chunks; `project_owned` identifica material produzido/controlado pelo projeto.

Uma futura distribuição pública do Knowledge deverá respeitar essas políticas por documento. Os PDFs, chunks e embeddings permanecem fora do Git. A política de distribuição também não é tratada como autorização automática para processamento por terceiros.

## Estado da IA

No Knowledge 1.2.0:

- recuperação lexical: implementada e baseline;
- recuperação semântica: implementada, dependente de índice local;
- recuperação híbrida RRF: implementada;
- construção de índice com provider OpenAI: disponível apenas por execução explícita;
- avaliação comparativa no corpus real: próxima etapa;
- LLM/RAG conversacional: ainda desabilitado.
