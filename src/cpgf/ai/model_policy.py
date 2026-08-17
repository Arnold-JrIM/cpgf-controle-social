from __future__ import annotations

LLM_MODEL_POLICY_VERSION = "1.0.0"
DEFAULT_LLM_MODEL = "gpt-4o-mini"


def project_llm_model() -> str:
    """Retorna o modelo LLM governado para os componentes do Assistente IA."""
    return DEFAULT_LLM_MODEL


def resolve_project_llm_model(requested_model: str | None = None) -> str:
    """Impede override silencioso do modelo governado do projeto."""
    governed = project_llm_model()
    if requested_model is not None and requested_model != governed:
        raise ValueError(
            f"modelo LLM não autorizado: {requested_model}; política exige {governed}"
        )
    return governed
