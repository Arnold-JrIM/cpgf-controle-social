from __future__ import annotations

import re

ANALYTICAL_DISCLAIMER = (
    "Os resultados representam sinais analíticos para direcionar a verificação e não "
    "constituem conclusão automática de fraude ou irregularidade."
)

_CATEGORICAL_CLAIMS = (
    re.compile(r"\b(é|foi|são|foram)\s+(uma\s+)?fraude\b", re.I),
    re.compile(r"\b(é|foi|são|foram)\s+(uma\s+)?irregularidade\b", re.I),
    re.compile(r"\b(comprovou|comprova|confirmou|confirma)\s+(a\s+)?fraude\b", re.I),
    re.compile(r"\b(fraudador|fraudulento|fraudulenta)\b", re.I),
)


class OutputGuardrailError(ValueError):
    """Narrativa incompatível com o caráter de triagem do projeto."""


def validate_narrative(text: str) -> str:
    value = str(text).strip()
    if any(pattern.search(value) for pattern in _CATEGORICAL_CLAIMS):
        raise OutputGuardrailError(
            "A narrativa contém conclusão categórica que excede a evidência analítica."
        )
    return value


def with_analytical_disclaimer(text: str) -> str:
    value = validate_narrative(text)
    if ANALYTICAL_DISCLAIMER.lower() in value.lower():
        return value
    return f"{value}\n\n{ANALYTICAL_DISCLAIMER}"
