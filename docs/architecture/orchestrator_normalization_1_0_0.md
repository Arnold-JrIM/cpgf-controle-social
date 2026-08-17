# Orchestrator Normalization 1.0.0

Status: **POST_HOC_DEVELOPMENT_POLICY**  
Versão: **1.0.0**

## Motivação

A primeira medição independente do OH1 mostrou uma separação clara entre reconhecimento de fontes e parametrização do plano. O `Semantic Evidence Orchestrator 1.0` acertou o conjunto de fontes em 141/168 execuções, enquanto o plano completo foi exato em apenas 38/168. DATA permaneceu forte, mas KNOWLEDGE teve 0/96 de exact match conjunto dos filtros, WEB teve 51/96 de parâmetros exatos e ocorreram nove violações estruturais.

O diagnóstico pós-hoc do PR #70 indicou, portanto, que a primeira intervenção deveria ser determinística e de menor privilégio, antes de qualquer tuning do prompt.

## Decisão

O Orchestrator 1.1 mantém o mesmo prompt e o mesmo modelo governado `gpt-4o-mini`. A nova camada `orchestrator_normalization.py` recebe o draft semântico estruturado e aplica regras determinísticas antes de o `EvidencePlan` ser aceito.

A ordem conceitual passa a ser:

```text
question
   |
   v
gpt-4o-mini -> structured draft
   |
   v
governed deterministic normalization
   |
   v
strict OrchestratorDecision
   |
   v
EvidencePlan
```

O SHA-256 do prompt permanece `9255a15213b96a9ba219fd43fb402e8d797842064c73d5a9e629d73f0b3269c2`. Dessa forma, este incremento isola a intervenção pós-LLM e evita atribuir eventual melhora a tuning de instrução.

## Regras

### Saneamento estrutural

Campos residuais emitidos para fontes marcadas como `selected=false` são removidos antes da validação Pydantic. Quando o modelo solicita esclarecimento e simultaneamente seleciona fontes, prevalece o esclarecimento: todas as fontes são limpas e nenhum worker pode ser disparado.

Essa regra busca eliminar falhas de contrato que não representam erro semântico da pergunta.

### Menor privilégio entre KNOWLEDGE e WEB

Quando WEB já foi selecionado, KNOWLEDGE só permanece no plano se a pergunta contiver intenção explícita de usar o corpus governado, como `corpus`, literatura, referências, fundamento jurídico, base normativa ou orientação institucional. A interpretação genérica de uma consulta externa não é razão suficiente para abrir uma segunda fonte documental.

A regra responde diretamente ao over-routing observado em `DATA+WEB`, sem criar exceções por ID de benchmark.

### Canonicalização KNOWLEDGE

`scopes`, `temporal_statuses` e `source_classes` deixam de ser aceitos passivamente como listas probabilísticas amplas. A camada aplica uma taxonomia lexical transparente e conservadora sobre `objective` e `query_hint` para identificar intenção normativa, institucional, metodológica, científica, acadêmica, de controle externo ou de contexto do projeto.

Quando a intenção não pode ser inferida com segurança, a política preserva os filtros válidos do draft em vez de inventar novos filtros. O `limit` de retrieval usa o default governado, exceto quando a própria consulta documental pede explicitamente uma quantidade de fontes.

### Canonicalização WEB

O número de resultados WEB não é derivado de números pertencentes à parcela DATA da pergunta. O default governado é usado salvo pedido explícito por quantidade de fontes/resultados externos.

`official_only=true` é aplicado quando há intenção explícita de fonte oficial. `max_age_days` só é criado quando a pergunta contém janela temporal explícita, como “últimos 30 dias”. A política não inventa uma janela de freshness ausente.

## Auditabilidade

Cada alteração determinística gera um código em `normalization_notes`, por exemplo:

- `DROPPED_KNOWLEDGE_WITHOUT_GOVERNED_INTENT`;
- `CANONICALIZED_KNOWLEDGE_SCOPES`;
- `CANONICALIZED_KNOWLEDGE_TEMPORAL`;
- `CANONICALIZED_KNOWLEDGE_SOURCE_CLASSES`;
- `CANONICALIZED_WEB_PARAMETERS`;
- `CLARIFICATION_FAIL_CLOSED`.

Os códigos acompanham `OrchestratorDecisionCall` e `EvidencePlanningRun`, permitindo distinguir o draft semântico da política determinística aplicada depois dele.

## Fronteiras

A camada de normalização não contém cliente OpenAI, não chama `responses.create`, não executa `TOOL_REGISTRY`, Retriever, busca WEB, DuckDB ou SQL. Ela não produz resposta ao usuário e não calcula score de risco, fraude ou irregularidade.

O modelo do projeto continua fixado em `gpt-4o-mini`.

## OH1 após a mudança

O OH1 é material conhecido desde a primeira medição oficial. Ele pode fundamentar diagnóstico e desenvolvimento, mas não pode ser usado para uma nova alegação de independência depois desta alteração.

O antigo `orchestration-holdout-v1-preflight` deixa de disparar em mudanças da candidata e passa a ser um workflow histórico manual, fixado no commit `ec87579fe285ddaf29b64bd05e3055ec3cb95736` da primeira medição. Isso preserva a reprodução do freeze prospectivo sem bloquear candidatas posteriores.

## Próximo passo

Depois de validar esta política em CI, a próxima evidência de generalização deve ser um novo holdout prospectivamente congelado, produzido sem exposição prévia ao Orchestrator 1.1. Nenhum resultado no OH1 poderá ser apresentado como nova avaliação independente.
