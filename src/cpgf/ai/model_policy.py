from __future__ import annotations

LLM_MODEL_POLICY_VERSION = "1.0.0"
DEFAULT_LLM_MODEL = "gpt-4o-mini"


def project_llm_model() -> str:
    """Retorna o modelo LLM governado para os componentes do Assistente IA."""
    return DEFAULT_LLM_MODEL
