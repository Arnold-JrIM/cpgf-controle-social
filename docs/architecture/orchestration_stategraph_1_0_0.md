# Orchestration StateGraph 1.0.0

## Objetivo

Este incremento implementa o primeiro `StateGraph` da arquitetura **Evidence-Orchestrated Assistant 2.0**. O escopo é exclusivamente estrutural: validar fan-out/fan-in, estado compartilhado e alinhamento com `EvidencePlan`/`EvidenceBundle` antes da conexão de fontes reais.

Nenhum LLM, Retriever, ferramenta de Serving, SQL ou busca web é executado neste estágio.

## Topologia

```text
START
  |
prepare
  |
  +-- EvidencePlan.needs == 0 ------------------+
  |                                               |
  +-- Send(need DATA) --------+                    |
  +-- Send(need KNOWLEDGE) ---+--> simulated_worker --> fan_in --> END
  +-- Send(need WEB) ---------+                    |
                                                  |
                           caminho direto --------+
```

O `prepare` apenas inicializa estado e registra os `need_id` que serão despachados. A função condicional `_dispatch` converte cada `EvidenceNeed` planejado em um `Send` para o mesmo worker simulado. Isso produz uma estrutura map-reduce: cada necessidade possui estado próprio durante o fan-out e os `EvidenceItem` retornados são agregados por reducer antes do `fan_in`.

## Governança do fan-out

O grafo não cria novas necessidades. Ele somente despacha os `EvidenceNeed` já presentes no `EvidencePlan` validado pelo contrato 1.0.

Consequências:

- um plano `{DATA}` produz somente um branch;
- um plano `{DATA, KNOWLEDGE}` produz dois branches;
- um plano `{DATA, KNOWLEDGE, WEB}` produz três branches;
- um plano vazio segue diretamente para o `fan_in`;
- nenhuma fonte é acionada por inferência implícita dentro do worker.

## Worker simulado

`simulated_worker` não consulta fonte real. Ele produz um `EvidenceItem` sintético claramente marcado com:

- `SIMULATED ONLY` no conteúdo;
- `SIMULATED ... EVIDENCE` na citação;
- `simulated://...` em `source_ref`;
- URL reservada `.invalid` quando a fonte é `WEB`.

O objetivo é exercitar os contratos específicos de cada fonte:

- `DATA` exige `ToolName` registrado e usa `retrieval_method="tool"`;
- `KNOWLEDGE` exige `document_id` e metadados documentais compatíveis;
- `WEB` exige `source_url`, `observed_at` e `retrieval_method="web"`.

Esses itens não podem ser interpretados como evidência material sobre gastos, normas ou fatos externos.

## Fan-in

O nó `fan_in` ordena os itens segundo a ordem das necessidades no `EvidencePlan` e constrói um único `EvidenceBundle`.

Isso garante que o resultado final seja determinístico mesmo que branches paralelos concluam em ordem distinta.

O próprio `EvidenceBundle` valida:

- `need_id` planejado;
- correspondência entre `need_id` e `EvidenceSource`;
- unicidade de `evidence_id`;
- completude das necessidades obrigatórias.

## Estado

`OrchestrationState` contém somente dados serializáveis e não secretos:

- `plan`;
- `current_need` durante branches;
- `worker_items` com reducer aditivo;
- `dispatched_need_ids`;
- `bundle`;
- `simulation_only`;
- `llm_called`.

Neste incremento `simulation_only=True` e `llm_called=False` são registrados pelo nó `prepare` e permanecem invariantes durante o fan-out.

## Política de modelo

A política de modelo do projeto passa a ser explícita:

```text
DEFAULT_LLM_MODEL = "gpt-4o-mini"
LLM_MODEL_POLICY_VERSION = "1.0.0"
```

O PR não realiza chamada ao modelo. A constante será consumida pelos futuros componentes que efetivamente utilizarem LLM, evitando modelos literais dispersos pelo código.

## Compatibilidade

`src/cpgf/ai/graph.py` e `prepare_assistant_state()` permanecem inalterados. O novo grafo vive em `orchestration_graph.py` e não substitui o fluxo atual de produção.

## Próximo passo

Após validação deste incremento, o próximo PR deve substituir progressivamente o worker simulado por dois executores reais e governados:

1. `Data Evidence Worker`, limitado ao `TOOL_REGISTRY` read-only;
2. `Knowledge Evidence Worker`, limitado ao corpus e ao Retrieval Planner governados.

O branch `WEB` deve continuar simulado até incremento próprio, para que freshness, política `official-first` e defesa contra conteúdo externo sejam introduzidas separadamente.
