# Notas arquiteturais — referência multi-agente RAG

## Referência examinada

Repositório público: `devfullcycle/techweekia9-multi-agents-rag`.

A referência implementa um sistema jurídico com um orquestrador e agentes especializados de pesquisa intra-processo, busca de casos semelhantes e análise, apoiados por RAG vetorial e estado de sessão.

Estas notas registram apenas **insights arquiteturais**. Nenhum código do repositório externo foi copiado e nenhuma mudança descrita abaixo altera o protocolo A/B/C antes da primeira execução real.

## Insights úteis para o CPGF — Controle Social

### 1. Orquestração explícita com responsabilidades estreitas

O repositório separa um agente raiz dos agentes especializados. Para o CPGF, o princípio é útil, mas deve ser aplicado de forma mais governada: a camada de interpretação não deve executar auditoria nem buscar livremente. Ela deve escolher uma rota/escopo fechado, e componentes especializados devem operar somente sobre fontes e ferramentas autorizadas.

Arquitetura futura candidata:

`pergunta -> interpretador semântico -> recuperadores especializados -> pacote de evidências -> sintetizador/verificador`

### 2. Separar evidência principal de evidência comparativa/contextual

A referência diferencia busca dentro do processo atual de busca em outros processos semelhantes. No CPGF, o paralelo mais útil é separar:

- **evidência primária/autoritativa**: normas vigentes, guias oficiais e decisões de controle externo;
- **evidência metodológica/contextual**: literatura científica, estudos acadêmicos e antecedentes interpretativos.

Uma pergunta `composite` pode consultar ambas, mas os resultados devem permanecer identificados por classe, autoridade, temporalidade e proveniência.

### 3. Compartilhar resultados entre etapas e evitar retrieval duplicado

Os agentes especializados gravam resultados no estado e o agente de análise é orientado a reutilizá-los antes de executar novas buscas. Para o projeto CPGF, isso sugere um objeto governado `EvidenceBundle`, imutável durante a síntese, contendo documentos/chunks, escopo, temporalidade, score de recuperação e proveniência.

Esse desenho reduz custo, evita divergência entre buscas repetidas e facilita auditoria da resposta final.

### 4. Estado de sessão deve estar vinculado ao contexto analítico

Na referência, a sessão é reiniciada quando o processo selecionado muda. Para o painel CPGF, o contexto conversacional futuro deve registrar explicitamente filtros relevantes — por exemplo período, UF, UG, trilha ou fornecedor — e invalidar/atualizar evidências quando esse contexto mudar.

Memória conversacional não deve transformar resultados antigos em fatos correntes sem nova consulta ao Serving/Knowledge governado.

### 5. Proveniência granular deve chegar à resposta

O agente de pesquisa da referência é instruído a citar seção e página dos trechos recuperados. O nosso corpus já possui metadados documentais governados; uma etapa futura deve elevar isso a contrato de resposta, preservando `document_id`, página/seção quando disponível, classe da fonte, autoridade e temporalidade.

Isso é especialmente importante para perguntas normativas e para explicar a base de cada trilha de auditoria.

### 6. Busca vetorial indexada é uma opção de escala, não uma necessidade imediata

A referência usa PostgreSQL + pgvector + HNSW. O princípio de indexação vetorial é relevante para corpora maiores, mas uma migração agora não se justifica automaticamente: o projeto CPGF já possui retrieval lexical, semântico e híbrido medido e um corpus governado relativamente pequeno.

Uma eventual migração deve ser motivada por métricas de escala/latência/qualidade, e não apenas por similaridade arquitetural.

### 7. Ingestão reprodutível e idempotente

A referência torna a ingestão reexecutável. Esse princípio converge com a governança do CPGF: corpus, chunks, embeddings e índices futuros devem poder ser reconstruídos a partir de manifests e hashes, com versões explícitas e sem depender de estado manual não rastreável.

## O que não adotar neste momento

- delegação autônoma irrestrita entre agentes;
- múltiplos LLMs executando buscas redundantes;
- migração imediata para Google ADK, LiteLLM ou pgvector;
- agente final com liberdade para transformar alertas T01–T09 em conclusões de irregularidade;
- memória conversacional como substituta de consulta às fontes governadas.

Esses elementos aumentariam custo e graus de liberdade antes de demonstrarmos ganho no problema mais básico de interpretação semântica.

## Sequência recomendada

1. concluir o experimento A/B/C com protocolo 1.0.1;
2. selecionar arquitetura somente se os critérios prospectivos forem atendidos;
3. congelar e medir a arquitetura escolhida em JH5 independente;
4. somente depois testar o Retriever/evidence grounding end-to-end;
5. introduzir, se necessário, recuperadores especializados por classe de evidência;
6. adicionar sintetizador/verificador final com contrato de citações e abstention;
7. avaliar política de fallback para reduzir chamadas ao LLM.

O principal insight da referência, portanto, não é “usar muitos agentes”, mas **separar responsabilidades e preservar o contexto/evidência entre etapas**. Essa interpretação é compatível com o desenho governado do projeto e evita transformar multiagentes em complexidade sem evidência de benefício.