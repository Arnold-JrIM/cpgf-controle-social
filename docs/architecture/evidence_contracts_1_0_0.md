# Contratos de evidência 1.0.0

## Objetivo

Este incremento materializa a primeira etapa do ADR `Evidence-Orchestrated Assistant 2.0` sem alterar o grafo de produção e sem executar LLM, Retriever, web ou ferramentas de dados.

O contrato primário do futuro Orchestrator passa a ser um `EvidencePlan` multi-rótulo. O plano declara **quais camadas de evidência** uma pergunta exige; componentes especializados serão responsáveis por obtê-las em incrementos posteriores.

## Fontes autorizadas

`EvidenceSource` possui somente três valores:

- `data`: fatos e agregações do Serving por ferramentas registradas e read-only;
- `knowledge`: normas, documentos oficiais, controle externo e literatura do corpus governado;
- `web`: informação externa/atual quando houver necessidade explícita de freshness ou insuficiência do corpus local.

O contrato 1.0 aceita no máximo uma necessidade agregada por fonte. Isso preserva uma fronteira simples para o futuro fan-out: no máximo três branches (`DATA`, `KNOWLEDGE`, `WEB`).

## `EvidenceNeed`

Cada necessidade contém:

- `need_id` estável;
- `source`;
- objetivo textual;
- indicação `required`;
- `freshness_required`;
- `query_hint` opcional;
- filtros documentais de escopo, temporalidade e classe de fonte quando aplicáveis;
- trilhas T01–T09 relacionadas;
- `tool_hints` somente para `DATA`;
- parâmetros estruturados e imutáveis.

Regras importantes:

- `tool_hints` não podem vazar para `KNOWLEDGE` ou `WEB`;
- filtros do corpus (`scopes`, `temporal_statuses`, `source_classes`) não pertencem a `DATA`;
- `scopes` do corpus governado não pertencem a `WEB`;
- nomes de parâmetros não podem se repetir;
- trilhas são normalizadas para T01–T09.

Essas regras não significam que o Orchestrator já esteja autorizado a escolher ferramentas em produção. Elas apenas definem o schema futuro e impedem cruzamento indevido de responsabilidades entre workers.

## `EvidencePlan`

O plano contém a pergunta, a justificativa e zero a três `EvidenceNeed`.

Zero necessidades é permitido para turnos que não exijam recuperação factual, por exemplo orientação de uso ou conteúdo explicitamente não evidencial. Quando houver necessidades, os `need_id` e as fontes devem ser únicos.

A propriedade `required_sources` fornece o conjunto de fontes obrigatórias para métricas futuras como **Evidence Source Set Exact Match**.

`legacy_route` é opcional e existe somente para compatibilidade/diagnóstico durante a transição. Ele não é a decisão principal da arquitetura 2.0.

## `EvidenceItem`

Um worker futuro retorna `EvidenceItem`, e não uma conclusão autônoma. Todo item possui:

- `evidence_id`;
- `need_id` de origem;
- `source`;
- conteúdo factual/documental;
- citação e referência de origem;
- parâmetros e versões envolvidos na produção da evidência.

A proveniência mínima depende da fonte:

### DATA

- exige `tool` do catálogo fechado;
- pode registrar parâmetros e versões de Serving/Rules/Motor/Geo;
- quando `retrieval_method` for informado, deve ser `tool`.

### KNOWLEDGE

- exige `document_id`;
- pode preservar `chunk_id`, página, seção, classe, autoridade, escopo, temporalidade, score e método de retrieval;
- não pode declarar ferramenta de Serving.

### WEB

- exige `source_url` e `observed_at`;
- pode registrar classe de fonte e demais metadados contextuais;
- não pode declarar ferramenta de Serving;
- quando `retrieval_method` for informado, deve ser `web`.

O contrato não contém campos como `fraud_score`, `irregularity`, `false_positive_probability` ou `risk_confirmed`.

## `EvidenceBundle`

O `EvidenceBundle` associa um plano aos itens produzidos pelos workers.

O bundle rejeita:

- `evidence_id` duplicado;
- evidência cujo `need_id` não conste do plano;
- evidência cuja fonte não corresponda à fonte planejada para aquele `need_id`.

O bundle pode ser parcial durante o futuro fan-in. Por isso, ausência temporária de evidência obrigatória não invalida o objeto. Em vez disso, ele expõe:

- `satisfied_need_ids`;
- `missing_required_need_ids`;
- `is_complete`.

Esse desenho permite distinguir tecnicamente **execução parcial** de **evidência suficiente para síntese** sem inventar um score de confiança.

## Imutabilidade e auditabilidade

Todos os modelos usam Pydantic com `extra="forbid"` e `frozen=True`. Coleções governadas são tuplas, e parâmetros/versões usam objetos estruturados em vez de dicionários mutáveis na fronteira principal.

O objetivo é permitir que um `EvidencePlan` e seu `EvidenceBundle` sejam serializados, persistidos e posteriormente inspecionados pelo Audit Ledger sem depender de texto livre entre agentes.

## Fora do escopo deste incremento

Este PR não implementa:

- Orchestrator LLM;
- LangGraph de produção;
- Data Worker;
- Knowledge Worker;
- Web/Freshness Worker;
- Synthesizer;
- Evidence Verifier;
- holdout de orquestração;
- execução de ferramenta, Retriever, SQL ou web.

O próximo incremento poderá usar estes contratos para construir um grafo de fan-out/fan-in ainda com workers simulados/determinísticos antes de conectar fontes reais.
