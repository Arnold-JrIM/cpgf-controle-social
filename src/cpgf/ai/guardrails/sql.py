from __future__ import annotations


class FreeSQLDisabledError(PermissionError):
    """SQL livre não integra a superfície de ferramentas do assistente."""


def reject_free_sql(_: str) -> None:
    """Falha sempre: o agente deve usar somente ferramentas registradas e parametrizadas."""
    raise FreeSQLDisabledError(
        "SQL livre está desabilitado. Use apenas ferramentas read-only registradas."
    )
