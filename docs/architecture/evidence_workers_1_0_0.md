# Evidence Workers 1.0.0

## Decisão

O PR #63 substitui o worker simulado do fluxo normal por dois executores reais e de baixo privilégio, preservando o Web/Freshness Worker em estado desabilitado. O harness integralmente simulado do PR #62 continua disponível apenas por chamada explícita de `run_simulated_orchestration()`.

A fronteira segue o princípio adotado no ADR do PR #60:

> o LLM interpreta e sintetiza; componentes governados recuperam fatos; evidências viajam com proveniência.

Nenhum LLM é chamado neste incremento. A política global continua fixada em `gpt-4o-mini` para os componentes semânticos que serão ativados em etapas posteriores.

## Data Evidence Worker

`execute_data_need()` aceita somente `EvidenceSource.DATA` e opera exclusivamente por `execute_tool()` sobre o `TOOL_REGISTRY` read-only existente.

Allowlist 1.0:

- `overview`;
- `trail_prevalence`;
- `top_ugs`;
- `top_suppliers`;
- `territorial_metric`;
- `territorial_ug_context`.

`methodology` permanece fora da fronteira DATA, apesar de existir no catálogo legado, porque não representa consulta factual ao Serving.

A versão 1.0 exige exatamente um `tool_hint` por necessidade DATA. Essa restrição é deliberada: o contrato atual ainda não possui parâmetros separados por ferramenta, e executar múltiplas ferramentas com um único dicionário de argumentos poderia produzir consumo ambíguo de parâmetros. Consultas multi-tool serão tratadas em evolução explícita do contrato, não por fallback silencioso.

O worker nunca recebe SQL. Ele converte os `EvidenceParameter` em `ToolRequest`, cuja validação permanece a cargo do modelo Pydantic associado à ferramenta registrada.

A evidência resultante preserva:

- nome da ferramenta;
- parâmetros estruturados;
- `serving_version`;
- `rules_version`;
- `motor_version`;
- `geo_version`;
- origem `serving_views`;
- resumo e registros retornados em payload limitado para o bundle.

Falhas de validação ou execução não são mascaradas. O worker retorna warning estruturado e nenhum `EvidenceItem`, mantendo a necessidade obrigatória como não satisfeita.

## Knowledge Evidence Worker

`retrieve_knowledge_need()` aceita somente `EvidenceSource.KNOWLEDGE` e usa a interface de busca já governada do corpus.

O worker **não reexecuta o Router/Planner 1.x**. Na arquitetura 2.0, `EvidencePlan/EvidenceNeed` já constituem o plano de recuperação. Replanejar a mesma pergunta com a lógica legada recriaria o problema de dupla decisão diagnosticado no JH4/JH5.

Assim, o executor aplica diretamente os filtros declarados no `EvidenceNeed`:

- `scopes`;
- `temporal_statuses`;
- `source_classes`;
- `query_hint`, quando existente;
- `limit` entre 1 e 20, com padrão 5.

Cada `SearchHit` vira um `EvidenceItem` separado, preservando:

- `document_id`;
- `chunk_id`;
- página;
- citação;
- classe da fonte;
- nível de autoridade;
- escopo;
- status temporal;
- score e método de retrieval;
- URL da fonte, quando disponível.

Ausência de hits não gera texto sintético. A necessidade permanece faltante no `EvidenceBundle`.

## Web/Freshness Worker

O branch WEB continua fail-closed em `disabled_web_need()`.

No fluxo normal ele:

- não chama internet;
- não cria evidência sintética;
- registra `WEB_WORKER_DISABLED_V1`;
- deixa a necessidade WEB obrigatória em `missing_required_need_ids`.

Isso impede que uma simulação seja confundida com evidência factual antes da implementação de política `official-first`, freshness, proveniência temporal e isolamento de conteúdo externo.

## StateGraph 1.1.0

O grafo mantém a topologia de fan-out/fan-in validada no PR #62:

`START -> prepare -> Send(EvidenceNeed...) -> evidence_worker -> fan_in -> END`

No modo normal, o `evidence_worker` despacha internamente para o executor compatível com a fonte. No modo de simulação explícita, continua produzindo os itens sintéticos usados apenas pelos testes estruturais.

O `fan_in` agrega tanto `EvidenceItem` quanto warnings por reducers e constrói um `EvidenceBundle` validado. A completude do bundle continua sendo determinada pela presença de evidência para cada necessidade obrigatória.

## Fail-closed

A versão 1.0 privilegia falha fechada:

- contexto DATA ausente -> nenhuma evidência;
- ferramenta ausente/não autorizada -> nenhuma evidência;
- erro Pydantic/execução -> nenhuma evidência;
- Retriever ausente -> nenhuma evidência;
- zero hits -> nenhuma evidência;
- parâmetros KNOWLEDGE desconhecidos -> nenhuma evidência;
- WEB -> nenhuma evidência até PR específico.

Nenhum desses estados é convertido em resposta inventada, score de confiança ou conclusão de irregularidade.

## Próximo incremento

Após este PR, o próximo componente deverá ser o Web/Freshness Worker governado, com fontes oficiais/primárias prioritárias, timestamp de observação, isolamento contra instruções presentes em páginas externas e testes determinísticos por fixtures/snapshots antes de consultas live.
