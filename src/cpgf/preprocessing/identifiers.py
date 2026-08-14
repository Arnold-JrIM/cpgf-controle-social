from __future__ import annotations

import re
import unicodedata
from typing import Any

PORTADOR_ID_BASELINE_VERSION = "1.0.0"
PORTADOR_ID_VERSION = "1.1.0"

_MISSING_TOKENS = {"", "-1"}
_WHITESPACE_RE = re.compile(r"\s+")
_DIGITS_RE = re.compile(r"[^0-9]")


def _text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def normalize_digits(value: Any) -> str | None:
    """Mantém apenas dígitos; retorna ``None`` quando não há identificador útil."""
    raw = _text(value)
    if raw in _MISSING_TOKENS:
        return None
    digits = _DIGITS_RE.sub("", raw)
    return digits or None


def normalize_name(value: Any) -> str:
    """Normaliza nome para comparação determinística: trim, espaços, caixa e acentos."""
    raw = _WHITESPACE_RE.sub(" ", _text(value)).upper()
    decomposed = unicodedata.normalize("NFKD", raw)
    return "".join(char for char in decomposed if not unicodedata.combining(char))


def normalize_ug(value: Any) -> str | None:
    """Normaliza código de UG; códigos numéricos são representados com seis dígitos."""
    raw = _text(value)
    if raw in _MISSING_TOKENS:
        return None
    if raw.isdigit():
        return raw.zfill(6)
    return raw


def is_sigilo_name(value: Any) -> bool:
    return "SIGILO" in normalize_name(value)


def build_portador_id_baseline(cpf_portador: Any, nome_portador: Any = None) -> str | None:
    """Reproduz a identidade histórica da Preparação 1.0.0.

    A baseline utiliza apenas os dígitos observáveis do CPF mascarado e invalida
    registros sem CPF útil ou com identificação do portador marcada como sigilo.
    """
    if is_sigilo_name(nome_portador):
        return None
    return normalize_digits(cpf_portador)


def build_portador_id(ug_id: Any, cpf_portador: Any, nome_portador: Any) -> str | None:
    """Constrói ``PORTADOR_ID`` da Preparação 1.1.0.

    A chave composta é ``UG_ID|CPF_NORMALIZADO|NOME_NORMALIZADO``. A UG é
    necessária porque o CPF disponibilizado é mascarado e não constitui
    identificador global inequívoco. O nome normalizado separa colisões
    nominativas observadas dentro da mesma UG.
    """
    cpf = build_portador_id_baseline(cpf_portador, nome_portador)
    ug = normalize_ug(ug_id)
    if cpf is None or ug is None:
        return None
    nome = normalize_name(nome_portador)
    return f"{ug}|{cpf}|{nome}"
