# Semantic Evidence Orchestrator 1.0.0

## Decisão

O PR #66 completa a camada de planejamento semântico da arquitetura **Evidence-Orchestrated Assistant 2.0**. Até o PR #65, o sistema já possuía contratos de evidência, StateGraph, workers DATA/KNOWLEDGE/WEB e pipeline de síntese/verificação, mas o `EvidencePlan` ainda precisava ser construído externamente.

O novo `Semantic Evidence Orchestrator` transforma a pergunta em um plano multi-rótulo governado. Sua pergunta central não é “qual agente deve responder?”, mas:

> de quais evidências esta pergunta precisa e quais executores estão autorizados a obtê-las?

O componente **planeja apenas**. Ele não consulta Serving, não executa Retriever, não navega na web e não redige a resposta final.

## Contrato semântico

O Orchestrator avalia três seleções independentes e combináveis:

- `DATA` — fatos quantitativos já materializados no Serving e acessíveis por ferramenta read-only;
- `KNOWLEDGE` — corpus governado normativo, institucional, de controle externo, científico ou acadêmico;
- `WEB` — informação externa que exija freshness ou fonte oficial externa não garantida pelo corpus.

A saída semântica é estruturada em três blocos fixos (`data`, `knowledge`, `web`) com `selected=true/false`. Essa forma evita duplicidade de fonte e torna o conjunto de evidências diretamente mensurável por **Evidence Source Set Exact Match**.

Após a chamada semântica, `build_evidence_plan()` converte a decisão em `EvidencePlan` canônico, sempre na ordem:

`DATA -> KNOWLEDGE -> WEB`

Os IDs também são determinísticos:

- `need-data`;
- `need-knowledge`;
- `need-web`.

A antiga `legacy_route` não participa da decisão e permanece `None`.

## Menor conjunto suficiente

O prompt 1.0 exige o menor conjunto de fontes suficiente para a pergunta.

Exemplos conceituais:

- “Quais UGs lideraram a priorização em 2025?” -> `DATA`;
- “Qual norma vigente disciplina o uso do CPGF?” -> `KNOWLEDGE`;
- “Houve atualização oficial recente fora do corpus?” -> `WEB`;
- “Compare o padrão observado nos dados com a norma vigente” -> `DATA + KNOWLEDGE`;
- pergunta que combine fatos, enquadramento documental e atualização externa -> `DATA + KNOWLEDGE + WEB`.

`WEB` não é fallback genérico para incerteza e `KNOWLEDGE` não deve ser adicionado a toda pergunta quantitativa apenas para aumentar contexto.

Essa política responde diretamente ao diagnóstico do JH5: uma rota composta única dizia que havia combinação, mas não representava precisamente **quais fontes** eram necessárias.

## DATA: plano executável, sem SQL

Quando `DATA` é selecionado, o Orchestrator deve escolher exatamente uma ferramenta presente na allowlist do Evidence Worker:

- `overview`;
- `trail_prevalence`;
- `top_ugs`;
- `top_suppliers`;
- `territorial_metric`;
- `territorial_ug_context`.

`methodology` permanece excluída da fronteira factual DATA.

O payload enviado ao modelo contém o catálogo das ferramentas e o JSON Schema dos respectivos argumentos. A decisão retornada é validada novamente pelo próprio modelo Pydantic da ferramenta antes de virar `EvidenceNeed`.

Consequências:

- parâmetros extras são rejeitados;
- parâmetros obrigatórios ausentes são rejeitados;
- defaults autorizados são normalizados deterministicamente;
- não existe campo SQL;
- o modelo não escolhe tabela, view ou expressão SQL.

Se a pergunta depender de um parâmetro obrigatório que não possa ser derivado sem adivinhação, a política orienta o modelo a solicitar esclarecimento em vez de inventar o filtro.

## KNOWLEDGE: filtros explícitos

Uma seleção `KNOWLEDGE` exige:

- `objective`;
- `query_hint`;
- pelo menos um `scope`;
- pelo menos um `temporal_status`.

As `source_classes` podem restringir a busca quando necessário. O único parâmetro operacional da versão 1.0 é `limit`, entre 1 e 20, com padrão 5.

O Orchestrator não reexecuta Router/Planner 1.x. O `EvidencePlan` 2.0 é o contrato primário; o worker aplica diretamente os filtros produzidos por ele.

## WEB: freshness explícita

Uma seleção `WEB` exige:

- `objective`;
- `query_hint`;
- `freshness_required=true`.

Os parâmetros são validados pelo mesmo `WebQueryOptions` usado pelo Web/Freshness Worker:

- `limit`;
- `official_only`;
- `max_age_days`.

Selecionar WEB não concede ao Orchestrator acesso à internet. A busca só ocorre posteriormente, no worker especializado e somente quando um adapter `WebSearcher` é explicitamente fornecido.

## Clarificação fail-closed

A decisão pode retornar `clarification_question` quando um filtro obrigatório não estiver disponível na pergunta sem adivinhação.

Nesse estado:

- nenhuma fonte pode estar selecionada;
- nenhum `EvidencePlan` executável é criado;
- `PlanningStatus` torna-se `clarification_required`;
- nenhum worker é chamado por este componente.

Erros de provider ou violações do plano resultam em `PlanningStatus.FAILED`, com warning estruturado. Não há fallback para rota legada.

## Modelo governado

O provider usa exclusivamente a política central:

`DEFAULT_LLM_MODEL = "gpt-4o-mini"`

O construtor de `OpenAIResponsesOrchestratorProvider` não aceita parâmetro `model`. A Responses API é usada com:

- JSON Schema estrito;
- `store=False`;
- metadados de response id, modelo, tokens e latência separados da decisão.

Também foi adicionado `resolve_project_llm_model()`, que rejeita explicitamente qualquer modelo diferente de `gpt-4o-mini` nas fronteiras que optarem por aceitar uma solicitação de modelo.

## Limites de autoridade

O Orchestrator não pode:

- responder ao mérito;
- recuperar evidência;
- executar ferramenta;
- executar Retriever;
- navegar na web;
- produzir SQL;
- concluir fraude, dolo, crime, ilegalidade ou irregularidade;
- atribuir score de risco/conformidade;
- transformar conteúdo externo em instrução;
- usar a rota legada como fallback oculto.

O LLM decide somente a **estrutura do plano de evidências**. Os fatos continuam sendo produzidos por componentes governados.

## Testes determinísticos

Os testes unitários cobrem:

- `DATA` executável e normalização de parâmetros;
- plano `DATA + KNOWLEDGE + WEB` e ordem canônica;
- falha fechada quando faltam argumentos DATA obrigatórios;
- bloqueio de `methodology` como ferramenta DATA;
- exigência de filtros explícitos em KNOWLEDGE;
- exigência de freshness em WEB;
- clarificação sem dispatch;
- falha do provider sem fallback;
- conjunto vazio de fontes sem evidência sintética;
- Responses API com schema estrito, `store=False` e `gpt-4o-mini`.

Os testes usam providers falsos. Este PR **não mede generalização live** do Orchestrator.

## Independência experimental

JH4 e JH5 são conjuntos conhecidos e não devem ser reutilizados para alegar generalização desta arquitetura. O diagnóstico do JH5 justificou a mudança de representação, mas não constitui avaliação independente do Orchestrator 2.0.

Após o merge deste PR, o código, prompt, schemas e políticas do Orchestrator 1.0 devem ser tratados como congelados para a próxima avaliação prospectiva.

A sequência metodologicamente preferível é:

1. congelar um novo **Orchestration Holdout** prospectivo, com casos `data_only`, `knowledge_only`, `web_only`, `data+knowledge`, `knowledge+web`, `data+web` e `all_three`, sem executar a avaliação live;
2. em PR separado, realizar a primeira medição com `gpt-4o-mini`, preservando o resultado bruto e seus hashes antes de qualquer ajuste.

As métricas centrais deverão incluir Evidence Source Set Exact Match, precisão/recall de seleção de fontes, under-routing, over-routing, seleção de ferramenta e exatidão de argumentos/filtros.
