# Knowledge 1.2.0 — recuperação semântica e híbrida

## Objetivo

O Knowledge 1.2.0 acrescenta uma camada de recuperação semântica e uma camada híbrida sobre o corpus documental governado no Knowledge 1.1.0. O objetivo deste incremento não é habilitar conversa com modelo de linguagem, mas criar uma infraestrutura de recuperação reproduzível que possa ser avaliada antes de qualquer etapa de RAG conversacional.

## Princípios preservados

1. O corpus continua sendo definido pelo catálogo governado de 45 documentos.
2. `retrieval_default`, `scope`, `temporal_status`, `source_class` e `document_id` permanecem filtros autoritativos também na recuperação vetorial.
3. Fontes históricas, materiais institucionais específicos da MB e documentos de descoberta não entram automaticamente na recuperação cidadã padrão quando `retrieval_default=false`.
4. O índice vetorial não é publicado no Git e não substitui a identidade documental baseada em caminho, SHA-256, tamanho e páginas.
5. A recuperação não produz conclusão automática de fraude ou irregularidade.
6. Nenhuma chamada a LLM é realizada pelo Knowledge 1.2.0.

## Recuperação lexical

`LexicalKnowledgeRetriever` permanece como baseline determinística. Ela utiliza tokenização normalizada, frequência de termo e IDF, com desempate determinístico por `chunk_id`.

## Recuperação semântica

`SemanticKnowledgeRetriever` recebe três componentes explicitamente separados:

- `chunks.parquet`, que contém texto e metadados governados;
- um índice vetorial com `chunk_id` e `embedding`;
- um `EmbeddingProvider`, responsável apenas por vetorizar a consulta.

Os vetores são normalizados e comparados por similaridade cosseno. Scores não positivos são descartados. O índice precisa cobrir integralmente os chunks utilizados pelo retriever e manter dimensionalidade única.

### Provider OpenAI

`OpenAIEmbeddingProvider` é uma implementação opcional. O padrão configurado é `text-embedding-3-small`, com 768 dimensões e `encoding_format="float"`. A chamada de rede somente ocorre quando o usuário executa explicitamente a construção do índice ou uma consulta semântica com esse provider e existe credencial disponível no ambiente.

O CI comum e o smoke de governança não realizam chamadas externas de embeddings. Os testes usam providers determinísticos falsos.

## Construção e validação do índice

O comando `scripts/build_semantic_index.py` lê `chunks.parquet`, gera os embeddings em lotes e grava localmente:

- `embeddings.parquet`;
- `embeddings_manifest.json`.

O manifesto registra versão do Knowledge, modelo, dimensionalidade, quantidade de chunks, SHA-256 do `chunks.parquet` de origem e SHA-256/tamanho do índice produzido.

`validate_semantic_index()` rejeita índice construído para outro corpus, hash divergente, cobertura incompleta, alteração na relação `chunk_id`/`document_id` ou dimensionalidade incompatível.

## Recuperação híbrida

`HybridKnowledgeRetriever` combina o ranking lexical e o ranking semântico por Reciprocal Rank Fusion (RRF), com `k=60` por padrão. A opção evita somar diretamente scores produzidos em escalas incomparáveis, preservando o papel de cada método e produzindo um ranking final independente da magnitude absoluta de BM25-like/TF-IDF e similaridade cosseno.

Cada `SearchHit` registra explicitamente `retrieval_method` como `lexical`, `semantic` ou `hybrid`.

## Distribuição e processamento externo

Os PDFs originais, os Parquet do corpus e o índice vetorial permanecem fora do Git. A política `distribution_policy` continua regulando distribuição do conteúdo documental, mas não é tratada como autorização automática para processamento por terceiros. Por isso, o provider externo é opt-in e a geração do índice real deve ocorrer somente após decisão explícita do responsável pelo projeto.

## Estado de validação

A implementação lexical, semântica e híbrida é validada em testes automatizados com provider sintético. O smoke do Knowledge 1.2.0 também verifica a página do Assistente IA sem realizar chamadas OpenAI reais. A avaliação comparativa de qualidade sobre o corpus local completo será tratada em incremento próprio, com consultas de referência e métricas de recuperação.
