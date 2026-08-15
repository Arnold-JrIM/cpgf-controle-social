from __future__ import annotations

import re

MAX_QUESTION_CHARS = 2_000

_MUTATION_PATTERNS = (
    re.compile(r"\b(drop|delete|truncate|alter|insert|update)\b\s+\b(table|from|into|set)\b", re.I),
    re.compile(r"\b(create|replace)\b\s+\b(table|view)\b", re.I),
    re.compile(r"\b(attach|detach|pragma|copy)\b\s+", re.I),
    re.compile(r"\b(recalcule|recalcular|recompute|reescreva|altere|mude)\b.*\bT0[1-9]\b", re.I),
)


class InputGuardrailError(ValueError):
    """Entrada incompatível com a superfície read-only do assistente."""


def validate_question(question: str) -> str:
    """Valida somente riscos explícitos; não tenta resolver prompt injection semanticamente."""
    text = str(question).strip()
    if not text:
        raise InputGuardrailError("A pergunta não pode ser vazia.")
    if len(text) > MAX_QUESTION_CHARS:
        raise InputGuardrailError(f"A pergunta excede {MAX_QUESTION_CHARS} caracteres.")
    if any(ord(char) < 32 and char not in "\n\t\r" for char in text):
        raise InputGuardrailError("A pergunta contém caracteres de controle não permitidos.")
    if any(pattern.search(text) for pattern in _MUTATION_PATTERNS):
        raise InputGuardrailError(
            "A solicitação pede mutação, SQL operacional ou recomputação de trilhas, "
            "capacidades não disponíveis ao assistente."
        )
    return text
