# Knowledge 1.1.0 — governança do corpus real do CPGF

## Objetivo

O Knowledge 1.1.0 substitui o catálogo semente do Knowledge 1.0.0 por um corpus governado e reproduzível, preservando a separação entre dados analíticos, documentos e futura camada de IA. O escopo permanece anterior a embeddings, índice vetorial e LLM.

## Corpus

O catálogo passa a registrar 45 referências: 44 arquivos locais da coleção documental organizada e uma referência normativa atual registrada inicialmente como metadata-only. Os PDFs permanecem fora do Git.

A coleção é segmentada em seis escopos:

- `cpgf_core`: normas, publicações oficiais e artigos diretamente ligados ao CPGF;
- `control_external`: decisões oficiais do TCU;
- `methodology`: fundamentos científicos e acadêmicos da análise e do controle social;
- `historical`: fontes revogadas, disponíveis somente para interpretação temporal;
- `institutional_mb`: documentos específicos da Marinha do Brasil, fora da recuperação cidadã padrão;
- `discovery`: obras amplas e documentos usados para descoberta de referências, não como evidência padrão.

## Fundamento direto e pertinência

`supports_trails` é reservado à relação curada em que a fonte sustenta diretamente uma regra ou método de T01–T09. `related_trails` indica apenas pertinência contextual ou metodológica. A existência de uma associação no catálogo não autoriza o assistente a afirmar que uma fonte fundamenta integralmente determinada trilha.

## Temporalidade

`temporal_status` distingue `current`, `historical` e `contextual`. Documentos históricos têm `retrieval_default=false`; seu uso exige opt-in explícito. Isso evita que uma norma revogada seja recuperada automaticamente para explicar o regime jurídico atual.

## Contrato local da fonte

Quando um arquivo local integra a baseline, o catálogo pode congelar:

- caminho relativo dentro de `data/knowledge/sources/`;
- SHA-256;
- tamanho em bytes;
- número de páginas.

O build valida esses atributos antes do chunking. Assim, substituir silenciosamente um PDF por outra edição produz falha explícita de contrato.

## Recuperação padrão

Dos 45 registros, 35 são elegíveis à recuperação lexical padrão. Fontes históricas, específicas da MB e materiais de descoberta ficam excluídos por padrão. O retriever permite filtros por classe, escopo, temporalidade e documento, além de opt-in para fontes não padrão.

## Macrofunção SIAFI 02.11.21

A cópia de referência é catalogada por caminho, SHA-256, tamanho e páginas. Embora visualmente legível, não apresenta texto extraível de forma confiável pelo pipeline atual; portanto, `ingest_content=false` e `retrieval_default=false` até que exista uma representação textual reproduzível. Não é aplicado OCR silencioso.

## Distribuição

Aquisição legal de um documento não é tratada como autorização automática de redistribuição. `distribution_policy` permanece independente da ingestão local. PDFs e artefatos processados ficam fora do Git por padrão; uma futura release pública deverá filtrar conteúdo conforme a política de cada documento.

## Fora do escopo

- embeddings e banco vetorial;
- recuperação híbrida;
- chamada a LLM;
- busca web;
- upload temporário de documentos;
- entrada por áudio;
- confirmação automática de fraude ou irregularidade.

O próximo incremento poderá comparar a baseline lexical governada com uma estratégia semântica/híbrida sem alterar o motor determinístico T01–T09.
