# Knowledge 1.0.0 — corpus normativo e científico

## Finalidade

O Knowledge 1.0.0 cria uma camada documental independente do Serving 1.5.0 e do Assistente IA. Seu objetivo é permitir que normas, publicações institucionais e literatura científica sejam catalogadas, processadas e recuperadas com proveniência antes da introdução de embeddings ou LLM.

## Separação de responsabilidades

- **Serving 1.5.0**: dados e sinais analíticos materializados;
- **Knowledge 1.0.0**: documentos e trechos com proveniência;
- **Assistente IA**: futura orquestração entre ferramentas e evidências.

O Knowledge não executa T01–T09 e não produz conclusão sobre fraude ou irregularidade.

## Fonte original, catálogo e artefatos

Os PDFs originais não são incluídos automaticamente no Git. O catálogo versionado registra `document_id`, título, autoria/autoridade, ano, citação, DOI/URL quando conhecido, classificação de fonte, política de distribuição e nome esperado do arquivo local.

Durante o build, cada arquivo disponível recebe SHA-256 e é transformado em chunks. Os artefatos derivados são:

- `documents.parquet` — catálogo materializado e estado de ingestão;
- `chunks.parquet` — trechos com página, citação, classe e autoridade;
- `knowledge_manifest.json` — versão, hashes, cardinalidades e parâmetros de chunking.

Os artefatos processados também permanecem fora do Git por padrão.

## Taxonomia de fontes

A classificação separa natureza da fonte e nível de autoridade. Exemplos:

- norma primária → `normative / primary_normative`;
- guia de órgão oficial → `institutional / official_institutional`;
- artigo revisado por pares → `scientific / scientific_peer_reviewed`;
- trabalho de congresso → `scientific / scientific_conference`;
- dissertação/tese → `academic / academic_thesis`;
- conteúdo futuro recuperado na web sem curadoria → `web / web_unclassified`.

Essa taxonomia foi desenhada para ser reutilizada futuramente na busca web, sem atribuir um percentual artificial de confiabilidade.

## Direitos e distribuição

O pipeline distingue quatro políticas:

- `public_official`;
- `open_license`;
- `metadata_only`;
- `project_owned`.

A classificação não substitui revisão jurídica. Em especial, `metadata_only` impede presumir que possuir acesso ao PDF autorize redistribuição pública do arquivo ou de um corpus derivado amplo.

## Extração e chunking

O loader 1.0.0 aceita PDF, Markdown e texto simples. PDFs preservam o número da página. O splitter é determinístico, usa tamanho e sobreposição registrados no manifesto e gera `chunk_id` por SHA-256 do conteúdo e contexto.

O build tolera fontes ausentes e as registra como `METADATA_ONLY`; `--require-all-sources` permite um gate estrito quando o corpus local estiver completo.

## Recuperação baseline

Antes de embeddings, o Knowledge oferece um retriever lexical determinístico. Sua função é validar:

1. a qualidade do texto extraído;
2. a granularidade dos chunks;
3. filtros por classe de fonte;
4. citações e páginas;
5. casos de teste conhecidos.

Esse retriever não é apresentado como solução semântica final. Embeddings e recuperação híbrida ficam para o PR seguinte.

## Corpus semente

O catálogo inicial registra sete fontes já utilizadas na pesquisa do projeto: CGU 2024, Portaria Normativa MF nº 1.344/2023, Manual DNIT 2024, artigo da Revista Controle sobre CPGF, trabalho ENAJUS sobre BI e fiscalização, artigo de 2025 sobre IA em auditoria pública e dissertação de 2018 sobre competência em informação e controle social.

O vínculo de uma fonte a T01–T09 significa pertinência para recuperação e investigação metodológica; **não significa que o documento sustente cientificamente cada regra listada**. A maturidade do fundamento de cada trilha continua sendo avaliada separadamente.

## Validação

O commit funcional `c1bda08276616ceefdb4357c520d5f5a55b11b15` foi validado em duas frentes.

O workflow `tests`, execução `31891558424`, concluiu com sucesso em Python 3.11 e Python 3.12, incluindo Ruff e pytest.

O workflow `knowledge-smoke`, execução `31891558351`, também concluiu com sucesso. O smoke comprovou que:

- o catálogo semente possui sete documentos;
- o build funciona mesmo sem os PDFs locais, registrando os sete como metadata-only e produzindo bundle válido;
- um corpus sintético com duas fontes gera dois chunks válidos;
- a recuperação lexical prioriza a fonte normativa esperada para consulta sobre suprimento de fundos e prestação de contas;
- a citação preserva a classificação `primary_normative`;
- a página `07_Assistente_IA.py` executa via `AppTest` sem exceção;
- embeddings e LLM permanecem desabilitados.

A primeira execução da branch (`31891298274`) falhou somente no Ruff pela ordenação de três imports no arquivo de testes. O commit `a19c2a10be4fa143dfc6b22759565c0887f901aa` corrigiu o estilo; as execuções posteriores passaram. Essa ocorrência é mantida no manifesto como trilha de validação.

Após o PASS, o workflow `knowledge-smoke` retorna a `workflow_dispatch` para evitar execução automática desnecessária.

## Fora do escopo

- embeddings;
- banco vetorial;
- OpenAI `file_search`;
- LLM;
- busca web;
- upload de documentos pelo usuário;
- áudio;
- publicação automática de PDFs ou chunks científicos.
