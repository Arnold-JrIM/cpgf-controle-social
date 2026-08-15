from __future__ import annotations

from cpgf.ai.guardrails.output import ANALYTICAL_DISCLAIMER
from cpgf.ai.router import route_question
from cpgf.ai.state import AssistantState


def prepare_assistant_state(question: str) -> AssistantState:
    """Prepara o turno sem chamar LLM nem executar ferramenta automaticamente."""
    decision = route_question(question)
    return AssistantState(
        question=str(question).strip(),
        route=decision.route,
        route_reason=decision.reason,
        notices=[ANALYTICAL_DISCLAIMER],
        llm_called=False,
    )
