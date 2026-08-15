from __future__ import annotations

from enum import StrEnum

import pandas as pd


class ValidationStatus(StrEnum):
    NAO_VALIDADO = "NAO_VALIDADO"
    EM_ANALISE = "EM_ANALISE"
    CONFIRMADO = "CONFIRMADO"
    JUSTIFICADO = "JUSTIFICADO"
    FALSO_POSITIVO = "FALSO_POSITIVO"
    ERRO_DADO = "ERRO_DADO"
    INCONCLUSIVO = "INCONCLUSIVO"


VALIDATION_STATUSES: tuple[str, ...] = tuple(status.value for status in ValidationStatus)
DEFAULT_VALIDATION_STATUS = ValidationStatus.NAO_VALIDADO
AUTOMATIC_CONFIRMED = False


def normalize_validation_status(status: str | ValidationStatus) -> ValidationStatus:
    if isinstance(status, ValidationStatus):
        return status
    try:
        return ValidationStatus(str(status).strip().upper())
    except ValueError as exc:
        raise ValueError(
            f"STATUS_VALIDACAO inválido: {status!r}. "
            f"Valores permitidos: {', '.join(VALIDATION_STATUSES)}"
        ) from exc


def attach_validation_status(
    frame: pd.DataFrame,
    *,
    status: str | ValidationStatus = DEFAULT_VALIDATION_STATUS,
    column: str = "STATUS_VALIDACAO",
    overwrite: bool = False,
) -> pd.DataFrame:
    """Adiciona status de validação sem converter sinal em confirmação automática."""
    result = frame.copy()
    normalized = normalize_validation_status(status).value

    if column in result.columns and not overwrite:
        existing = result[column].astype("string")
        invalid = existing.notna() & ~existing.isin(VALIDATION_STATUSES)
        if invalid.any():
            examples = existing.loc[invalid].drop_duplicates().head(5).tolist()
            raise ValueError(f"{column} contém valores inválidos: {examples}")
        result[column] = existing.fillna(normalized)
        return result

    result[column] = pd.Series(normalized, index=result.index, dtype="string")
    return result


def validation_is_human_confirmed(status: str | ValidationStatus) -> bool:
    return normalize_validation_status(status) == ValidationStatus.CONFIRMADO
