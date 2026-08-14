from __future__ import annotations

import re
import unicodedata
from typing import Any

import pandas as pd

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
    raw = _text(value)
    if raw in _MISSING_TOKENS:
        return None
    digits = _DIGITS_RE.sub("", raw)
    return digits or None


def normalize_name(value: Any) -> str:
    raw = _WHITESPACE_RE.sub(" ", _text(value)).upper()
    decomposed = unicodedata.normalize("NFKD", raw)
    return "".join(char for char in decomposed if not unicodedata.combining(char))


def normalize_ug(value: Any) -> str | None:
    raw = _text(value)
    if raw in _MISSING_TOKENS:
        return None
    if raw.isdigit():
        return raw.zfill(6)
    return raw


def is_sigilo_name(value: Any) -> bool:
    return "SIGILO" in normalize_name(value)


def is_sem_inform_name(value: Any) -> bool:
    return "SEM INFORM" in normalize_name(value)


def build_portador_id_baseline(cpf_portador: Any, nome_portador: Any = None) -> str | None:
    if is_sigilo_name(nome_portador):
        return None
    return normalize_digits(cpf_portador)


def build_portador_id(ug_id: Any, cpf_portador: Any, nome_portador: Any) -> str | None:
    cpf = build_portador_id_baseline(cpf_portador, nome_portador)
    ug = normalize_ug(ug_id)
    if cpf is None or ug is None:
        return None
    nome = normalize_name(nome_portador)
    return f"{ug}|{cpf}|{nome}"


def build_favorecido_id(cnpj_cpf: Any, nome_favorecido: Any = None) -> str | None:
    if is_sigilo_name(nome_favorecido) or is_sem_inform_name(nome_favorecido):
        return None
    return normalize_digits(cnpj_cpf)


def _series_text(series: pd.Series) -> pd.Series:
    return series.astype("string").fillna("").str.strip()


def normalize_digits_series(series: pd.Series) -> pd.Series:
    raw = _series_text(series)
    digits = raw.str.replace(r"[^0-9]", "", regex=True)
    return digits.mask(raw.isin(_MISSING_TOKENS) | digits.eq(""), pd.NA).astype("string")


def normalize_name_series(series: pd.Series) -> pd.Series:
    raw = _series_text(series).str.replace(r"\s+", " ", regex=True).str.upper()
    return raw.str.normalize("NFKD").str.encode("ascii", "ignore").str.decode("ascii")


def normalize_ug_series(series: pd.Series) -> pd.Series:
    raw = _series_text(series)
    result = raw.copy()
    numeric = raw.str.fullmatch(r"\d+")
    result.loc[numeric] = raw.loc[numeric].str.zfill(6)
    return result.mask(raw.isin(_MISSING_TOKENS), pd.NA).astype("string")


def build_portador_id_baseline_series(cpf: pd.Series, nome: pd.Series) -> pd.Series:
    cpf_norm = normalize_digits_series(cpf)
    nome_norm = normalize_name_series(nome)
    return cpf_norm.mask(nome_norm.str.contains("SIGILO", regex=False), pd.NA).astype("string")


def build_portador_id_series(ug: pd.Series, cpf: pd.Series, nome: pd.Series) -> pd.Series:
    ug_norm = normalize_ug_series(ug)
    cpf_norm = build_portador_id_baseline_series(cpf, nome)
    nome_norm = normalize_name_series(nome)
    result = ug_norm + "|" + cpf_norm + "|" + nome_norm
    return result.mask(ug_norm.isna() | cpf_norm.isna(), pd.NA).astype("string")


def build_favorecido_id_series(cnpj_cpf: pd.Series, nome: pd.Series) -> pd.Series:
    identifier = normalize_digits_series(cnpj_cpf)
    nome_norm = normalize_name_series(nome)
    invalid = nome_norm.str.contains("SIGILO", regex=False) | nome_norm.str.contains("SEM INFORM", regex=False)
    return identifier.mask(invalid, pd.NA).astype("string")
