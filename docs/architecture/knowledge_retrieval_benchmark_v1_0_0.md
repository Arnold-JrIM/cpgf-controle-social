# Benchmark de Recuperação do Knowledge 1.0.0

## Objetivo

O Benchmark de Recuperação 1.0.0 cria um conjunto documental separado dos benchmarks de roteamento do Assistente. Seu objetivo é medir se os mecanismos do Knowledge recuperam documentos adequados para fundamentar perguntas conceituais, normativas, metodológicas e de controle externo relacionadas ao CPGF.

O benchmark foi congelado **antes da primeira medição no `chunks.parquet` real**. Assim, a baseline lexical e as comparações semântica e híbrida não participam da construção dos gabaritos.

## Unidade de avaliação

Embora os retrievers retornem chunks, a avaliação é realizada em **nível de documento**. Múltiplos chunks do mesmo documento são contraídos para uma única posição no ranking antes do cálculo das métricas. Essa escolha evita premiar artificialmente um método apenas porque um documento longo aparece repetidas vezes entre os primeiros chunks.

Para `k=5`, o contrato calcula:

- **Hit Rate@5**: proporção de perguntas com ao menos um documento-gabarito entre os cinco primeiros documentos distintos;
- **Mean Document Recall@5**: média da fração de documentos-gabarito recuperados entre os cinco primeiros;
- **MRR**: média do inverso da posição do primeiro documento-gabarito;
- **MAP@5**: média da precisão média até a quinta posição, considerando múltiplos documentos relevantes.

Os resultados devem ser apresentados em dois modos: **governed**, aplicando os escopos e estados temporais previstos no caso, e **unfiltered**, sem esses filtros esperados. A comparação permite verificar se a governança documental ajuda ou prejudica a recuperação, sem confundir esse efeito com o algoritmo de busca.

## Composição congelada

O arquivo `data/benchmarks/knowledge_retrieval_v1_0_0.csv` contém 30 casos:

| Categoria | Casos |
|---|---:|
| normativa | 15 |
| combinação de fontes | 8 |
| metodologia | 6 |
| controle externo | 1 |

O conjunto referencia 25 documentos do catálogo, dos quais 24 são documentos-gabarito. Cada documento-gabarito deve estar habilitado para recuperação padrão, possuir contrato de ingestão de conteúdo e ter caminho local esperado. Fontes apenas catalogadas, sem conteúdo local, podem permanecer como apoio, mas não são tratadas como recuperáveis no gabarito.

SHA-256 congelado:

`6633babe7e17f4c0fefb0523ea477a11257bad87d3c0bc258dea7db1c33c1777`

Commit de congelamento do conteúdo antes da primeira medição real:

`8e5b49db673c863fe7b9a0c889c2a79457068dec`

## Relação com as trilhas

O benchmark documental possui casos relacionados a T02, T03, T04, T05, T07, T08 e T09 porque o corpus congelado contém referências que podem ser usadas diretamente para essas perguntas. T01 e T06 não foram artificialmente associados a documentos apenas para alcançar cobertura numérica de T01–T09.

Essa ausência **não significa exclusão, irrelevância ou invalidação de T01 e T06**. Uma trilha pode continuar sendo útil como mecanismo de triagem mesmo quando o corpus atual ainda não oferece uma fonte normativa ou científica suficientemente direta para compor um gabarito documental. A decisão de manter ou alterar uma trilha não deve ser tomada pela sobreposição estatística ou pela ausência neste benchmark isoladamente.

## Métodos comparáveis

O avaliador `scripts/evaluate_knowledge_retrieval.py` foi preparado para aplicar o mesmo conjunto aos três mecanismos já contratados pelo Knowledge 1.2.0:

1. **lexical**, inteiramente local;
2. **semantic**, usando índice semântico previamente construído e validado;
3. **hybrid**, por Reciprocal Rank Fusion (RRF) entre rankings lexical e semântico.

A execução semântica/híbrida com o provider OpenAI atual exige `--allow-external-embeddings` de forma explícita. Sem esse parâmetro nenhuma pergunta do benchmark é enviada ao serviço externo. Credenciais não integram o benchmark, o catálogo, o manifesto nem os artefatos versionados.

## Separação entre corpus, Git e avaliação

Os PDFs originais permanecem em `data/knowledge/sources/` e os artefatos processados em `data/knowledge/processed/`, ambos fora do Git conforme a governança do Knowledge. O índice vetorial também permanece local. O Git versiona somente o benchmark, o código do avaliador, contratos, testes, documentação e manifestos de evidência.

Por esse motivo, o CI desta versão valida a estrutura do benchmark e seus documentos contra o catálogo, mas **não produz uma pontuação de recuperação sobre conteúdo sintético ou incompleto**. A primeira pontuação autoritativa deve usar o bundle real construído localmente a partir do corpus governado.

## Estado ao congelamento

- Benchmark de Recuperação: **1.0.0**;
- Knowledge: **1.2.0**;
- APP: **0.11.0-dev**;
- casos: **30**;
- documentos-gabarito distintos: **24**;
- casos sensíveis à vigência: **3**;
- primeira medição no corpus real: **não realizada**;
- LLM: **não chamado**;
- SQL: **não executado**;
- embeddings externos: **desabilitados por padrão**.

Os resultados futuros deste benchmark não demonstrarão, por si sós, qualidade da resposta do chatbot, validade jurídica de uma conclusão, irregularidade, fraude ou desempenho de produção. Eles medirão exclusivamente a capacidade do mecanismo de recuperação de posicionar documentos-gabarito no ranking definido.
