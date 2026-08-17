# LLM Model Policy 1.0.0

O Assistente IA do projeto adota `gpt-4o-mini` como modelo LLM padrão e governado.

A política é materializada em `src/cpgf/ai/model_policy.py`:

```text
DEFAULT_LLM_MODEL = "gpt-4o-mini"
LLM_MODEL_POLICY_VERSION = "1.0.0"
```

Componentes futuros que chamarem LLM devem consumir essa política em vez de declarar modelos literais localmente. Mudança de modelo deverá ocorrer em incremento próprio, com justificativa, versionamento e, quando afetar comportamento mensurável, nova avaliação prospectiva.

O StateGraph 1.0.0 não chama LLM. A política é registrada antecipadamente para que Orchestrator, Synthesizer e Evidence Verifier compartilhem o mesmo modelo quando forem ativados.
