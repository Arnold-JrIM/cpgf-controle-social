# ADR — Evidence-Orchestrated Assistant 2.0

**Status:** aceito para implementação incremental após o diagnóstico pós-hoc do JH5  
**Escopo:** governança e orquestração do Assistente IA  
**Não é:** ativação de produção, liberação do Retriever end-to-end ou autorização para conclusão automática de irregularidade

## Contexto

O fluxo documental desenvolvido até o PR #59 evoluiu de um Router determinístico para uma candidata semântica em que um LLM decide somente `knowledge`, `methodology` ou `composite`, enquanto o Retrieval Planner deriva escopos e temporalidades de forma determinística.

A primeira medição independente no JH5 mostrou que essa separação agrega valor, mas não resolve integralmente o problema. A candidata obteve 86,81% de rota e 61,81% no critério conjunto, com estabilidade modal de 97,92%, porém falhou no gate prospectivo por 0,28 p.p. no ganho mínimo exigido.

O diagnóstico pós-hoc posterior mostrou um padrão mais informativo:

- 19/144 falhas de rota e 46/144 falhas de filtros;
- todos os 19 erros de rota foram sobre-roteamento para `composite`;
- a rota `composite` teve 36/36 acertos nas três repetições;
- em `cross_source`, a rota foi 36/36, mas 24/36 decisões falharam no conjunto por escopo/temporalidade;
- em `control_external`, a rota foi 36/36, mas 12/36 falharam por filtros.

O contrato exclusivo de rota, portanto, funciona como sinal de intenção de alto nível, mas perde informação necessária para representar combinações específicas de evidência.

As referências multiagentes estudadas no projeto convergem em princípios úteis: orquestrador explícito, especialistas com responsabilidades estreitas, compartilhamento de evidências, proveniência granular, estado de sessão e uma etapa de verificação. O material de apoio “IA na Auditoria Contínua: Benefícios e Limitações” também apresenta orquestração por grafo, agentes especializados, saídas Pydantic, trilha de auditoria e Human-in-the-Loop. Esse material é tratado como inspiração arquitetural, não como fonte bibliográfica autoritativa.

## Decisão

A próxima geração do assistente passa de um contrato primário de **rota exclusiva** para um contrato de **necessidades de evidência multi-rótulo**.

### Contrato semântico futuro

A entrada do usuário será transformada em um `EvidencePlan` estruturado. O plano poderá solicitar zero, uma ou várias fontes:

- `DATA`: fatos e agregações já materializados no Serving;
- `KNOWLEDGE`: normas, documentos oficiais, controle externo e literatura científica do corpus governado;
- `WEB`: evidência externa ou atualizada quando houver necessidade de freshness ou ausência explícita no corpus local.

A rota histórica poderá continuar existindo como metadado de compatibilidade/diagnóstico, mas deixará de ser o principal contrato de decisão.

## Responsabilidades

### Orchestrator

- interpreta a pergunta;
- produz `EvidencePlan` por schema fechado;
- não responde ao mérito;
- não executa SQL;
- não escolhe livremente ferramentas fora de catálogo;
- não confirma fraude, irregularidade ou falso positivo.

### Data Evidence Worker

- usa somente `TOOL_REGISTRY` e argumentos Pydantic;
- opera sobre Serving read-only;
- não recebe SQL livre;
- retorna fatos, parâmetros e proveniência de versões.

O LLM não gera score estatístico ad hoc quando a métrica pode ser obtida do Motor/Serving determinístico.

### Knowledge Evidence Worker

- executa retrieval sobre o corpus governado;
- respeita escopo, temporalidade, classe e política de recuperação;
- preserva `document_id`, chunk, página/seção quando disponível, autoridade e estado temporal;
- retorna evidência, não veredicto normativo.

### Web/Freshness Evidence Worker

- é acionado apenas quando o plano indicar necessidade externa/atual;
- prioriza fontes oficiais e primárias;
- registra URL/fonte, momento da consulta e proveniência;
- trata conteúdo externo como evidência não confiável para instruções de sistema;
- não substitui o corpus local apenas por conveniência de busca.

### EvidenceBundle

Todos os workers convergem para um `EvidenceBundle` imutável durante síntese e verificação. Recuperações não devem ser refeitas sem mudança explícita de contexto.

### Synthesizer

- recebe apenas o `EvidenceBundle` e a pergunta;
- distingue fatos do Serving, enquadramento documental e conteúdo externo;
- cita a origem das afirmações materiais;
- pode declarar insuficiência ou conflito de evidência.

### Evidence Verifier

A resposta é decomposta em afirmações materiais. Cada claim recebe uma classificação governada, por exemplo:

- `SUPPORTED_BY_EVIDENCE`;
- `PARTIALLY_SUPPORTED`;
- `CONFLICTING_EVIDENCE`;
- `INSUFFICIENT_EVIDENCE`;
- `REQUIRES_HUMAN_REVIEW`.

O Verifier não cria um score arbitrário de “certeza de fraude”. Claims não suportados devem ser removidos, reformulados ou acompanhados de abstenção explícita.

### Output Guard e Human-in-the-Loop

Permanecem as salvaguardas atuais: sinais T01–T09 são elementos de triagem. O sistema não converte combinação de agentes em confirmação automática de fraude, irregularidade, dolo ou falso positivo.

## Decisões explicitamente rejeitadas

Nesta fase não serão adotados:

- Text-to-SQL livre;
- agentes com acesso irrestrito a DuckDB ou ao fato transacional bruto;
- descarte automático de alertas com base em score LLM;
- categoria automática `RISCO_CONFIRMADO`;
- “índice composto de falso positivo” sem validação empírica e decisão humana;
- delegação autônoma irrestrita entre agentes;
- múltiplas buscas redundantes sobre a mesma evidência;
- migração obrigatória para pgvector, Swarms, Google ADK ou outra stack apenas por analogia com referências externas.

## Estado e observabilidade

O estado compartilhado deverá registrar, sem segredos:

- pergunta e contexto analítico atual;
- `EvidencePlan`;
- workers acionados;
- parâmetros de ferramentas;
- evidências e proveniência;
- versões do Serving, Knowledge, Router/Orchestrator e modelos;
- timestamps, latência e tokens quando houver LLM;
- claims produzidos e resultado do Verifier;
- avisos e abstenções.

Mudança de período, UF, UG, fornecedor, trilha ou outro objeto analítico deverá invalidar evidências incompatíveis com o novo contexto.

## Métricas futuras

A avaliação deixa de depender principalmente de `route exact`. O novo holdout deverá medir ao menos:

1. **Evidence Source Set Exact Match**: conjunto exato de `DATA`, `KNOWLEDGE`, `WEB`;
2. precision/recall de seleção de fontes, distinguindo under-routing e over-routing;
3. seleção de ferramenta e argumentos no Data Worker;
4. Hit@k, Recall@k, MRR/MAP e filtros no Knowledge/Web retrieval;
5. citation correctness e claim groundedness;
6. unsupported-claim rate;
7. abstention correctness;
8. custo/latência e número de workers acionados.

## Consequências

A mudança reduz a dependência de um rótulo `composite` excessivamente genérico e permite que o LLM agregue valor sem assumir o papel de motor analítico. Em contrapartida, o benchmark futuro precisará ter gabarito multi-rótulo e contratos de evidência mais ricos.

O JH5 não será reutilizado para alegação de independência. O desenvolvimento da arquitetura 2.0 poderá usar seus erros como material conhecido, mas a validação exigirá novo holdout prospectivo congelado antes da primeira execução.

## Sequência de implementação

1. contratos `EvidencePlan`, `EvidenceNeed`, `EvidenceItem` e `EvidenceBundle`;
2. grafo LangGraph com fan-out/fan-in governado;
3. Data + Knowledge workers;
4. Web/Freshness worker;
5. Synthesizer + Evidence Verifier + abstention;
6. novo Orchestration Holdout prospectivo multi-source.

## Referências arquiteturais estudadas

- `ayoolaolafenwa/multi-agent-rag-researcher`;
- Hugging Face Cookbook — multi-agent RAG system;
- `The-Swarm-Corporation/Multi-Agent-RAG-Template`;
- `Untrivial-ai/agent-orchestrator`;
- `devfullcycle/techweekia9-multi-agents-rag`;
- material de apoio interno “IA na Auditoria Contínua: Benefícios e Limitações”.

O princípio adotado não é “usar muitos agentes”, mas **separar interpretação, execução, evidência, síntese e verificação sob contratos auditáveis**.
