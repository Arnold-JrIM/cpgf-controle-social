from __future__ import annotations

from collections.abc import Mapping

import pandas as pd

from cpgf.version import MOTOR_VERSION, PREPARATION_VERSION, RULES_VERSION

from .evidence import governance_for_trail
from .families import family_for_trail, normalize_trail_code
from .validation import (
    DEFAULT_VALIDATION_STATUS,
    ValidationStatus,
    attach_validation_status,
)


EVIDENCE_ID_CANDIDATES: tuple[str, ...] = (
    "ID_SINAL",
    "ID_EPISODIO",
    "ID_GRUPO",
    "ID_CONTEXTO",
)

GOVERNANCE_COLUMNS: tuple[str, ...] = (
    "ID_EVIDENCIA",
    "TRILHA",
    "FAMILIA_EVIDENCIA",
    "NOME_FAMILIA_EVIDENCIA",
    "TIPO_EVIDENCIA",
    "PAPEL_EVIDENCIA",
    "UNIDADE_PRIMARIA",
    "CONVERGENCIA_NUCLEO",
    "STATUS_VALIDACAO",
    "VERSAO_PREPARACAO",
    "VERSAO_REGRAS",
    "VERSAO_MOTOR",
)


def infer_evidence_id_column(frame: pd.DataFrame) -> str:
    for candidate in EVIDENCE_ID_CANDIDATES:
        if candidate in frame.columns:
            return candidate
    raise ValueError(
        "Não foi possível identificar a coluna de evidência. "
        f"Esperado um de: {', '.join(EVIDENCE_ID_CANDIDATES)}."
    )


def tag_evidence(
    frame: pd.DataFrame,
    trail_code: str,
    *,
    evidence_id_column: str | None = None,
    validation_status: str | ValidationStatus = DEFAULT_VALIDATION_STATUS,
) -> pd.DataFrame:
    """Acrescenta o contrato de governança sem alterar cardinalidade ou regra da trilha."""
    code = normalize_trail_code(trail_code)
    family = family_for_trail(code)
    governance = governance_for_trail(code)
    result = frame.copy()

    if evidence_id_column is None:
        if result.empty and not any(col in result.columns for col in EVIDENCE_ID_CANDIDATES):
            result["ID_EVIDENCIA"] = pd.Series(index=result.index, dtype="string")
        else:
            evidence_id_column = infer_evidence_id_column(result)

    if evidence_id_column is not None:
        if evidence_id_column not in result.columns:
            raise ValueError(f"Coluna de evidência ausente: {evidence_id_column}")
        result["ID_EVIDENCIA"] = result[evidence_id_column].astype("string")
        duplicated = result["ID_EVIDENCIA"].notna() & result["ID_EVIDENCIA"].duplicated(
            keep=False
        )
        if duplicated.any():
            examples = result.loc[duplicated, "ID_EVIDENCIA"].drop_duplicates().head(5).tolist()
            raise ValueError(
                "ID_EVIDENCIA deve ser único dentro da saída primária da trilha; "
                f"duplicados encontrados: {examples}"
            )

    result["TRILHA"] = code
    result["FAMILIA_EVIDENCIA"] = family.code
    result["NOME_FAMILIA_EVIDENCIA"] = family.name
    result["TIPO_EVIDENCIA"] = governance.evidence_type.value
    result["PAPEL_EVIDENCIA"] = governance.role.value
    result["UNIDADE_PRIMARIA"] = governance.primary_unit
    result["CONVERGENCIA_NUCLEO"] = governance.convergence_core
    result = attach_validation_status(result, status=validation_status)
    result["VERSAO_PREPARACAO"] = PREPARATION_VERSION
    result["VERSAO_REGRAS"] = RULES_VERSION
    result["VERSAO_MOTOR"] = MOTOR_VERSION

    governance_columns = [column for column in GOVERNANCE_COLUMNS if column in result.columns]
    payload_columns = [column for column in result.columns if column not in governance_columns]
    return result.loc[:, governance_columns + payload_columns].reset_index(drop=True)


def consolidate_evidence(
    primary_frames: Mapping[str, pd.DataFrame],
    *,
    validation_status: str | ValidationStatus = DEFAULT_VALIDATION_STATUS,
) -> pd.DataFrame:
    """Concatena saídas primárias já calculadas; não recalcula nem deduplica trilhas."""
    tagged: list[pd.DataFrame] = []
    for trail_code, frame in primary_frames.items():
        tagged.append(
            tag_evidence(
                frame,
                trail_code,
                validation_status=validation_status,
            )
        )

    if not tagged:
        return pd.DataFrame(columns=GOVERNANCE_COLUMNS)

    result = pd.concat(tagged, ignore_index=True, sort=False)
    result["STATUS_VALIDACAO"] = result["STATUS_VALIDACAO"].astype("string")
    return result
