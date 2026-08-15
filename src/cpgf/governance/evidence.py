from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from .families import normalize_trail_code


class EvidenceType(StrEnum):
    FATO_DETERMINISTICO = "FATO_DETERMINISTICO"
    PADRAO_COMPORTAMENTAL = "PADRAO_COMPORTAMENTAL"
    SINAL_ESTATISTICO = "SINAL_ESTATISTICO"
    CONTEXTO_NORMATIVO = "CONTEXTO_NORMATIVO"
    PADRAO_ESTRUTURAL = "PADRAO_ESTRUTURAL"


class EvidenceRole(StrEnum):
    NUCLEO = "NUCLEO"
    CONTEXTO = "CONTEXTO"


@dataclass(frozen=True)
class TrailGovernance:
    trail: str
    evidence_type: EvidenceType
    role: EvidenceRole
    primary_unit: str
    convergence_core: bool


TRAIL_GOVERNANCE: dict[str, TrailGovernance] = {
    "T01": TrailGovernance(
        trail="T01",
        evidence_type=EvidenceType.FATO_DETERMINISTICO,
        role=EvidenceRole.NUCLEO,
        primary_unit="TRANSACAO",
        convergence_core=True,
    ),
    "T02": TrailGovernance(
        trail="T02",
        evidence_type=EvidenceType.FATO_DETERMINISTICO,
        role=EvidenceRole.NUCLEO,
        primary_unit="TRANSACAO",
        convergence_core=True,
    ),
    "T03": TrailGovernance(
        trail="T03",
        evidence_type=EvidenceType.PADRAO_COMPORTAMENTAL,
        role=EvidenceRole.NUCLEO,
        primary_unit="GRUPO_TRANSACOES",
        convergence_core=True,
    ),
    "T04": TrailGovernance(
        trail="T04",
        evidence_type=EvidenceType.PADRAO_COMPORTAMENTAL,
        role=EvidenceRole.NUCLEO,
        primary_unit="UG_FORNECEDOR_DATA_VALOR",
        convergence_core=True,
    ),
    "T05": TrailGovernance(
        trail="T05",
        evidence_type=EvidenceType.PADRAO_COMPORTAMENTAL,
        role=EvidenceRole.NUCLEO,
        primary_unit="UG_FORNECEDOR_ANO_EPISODIO",
        convergence_core=True,
    ),
    "T06": TrailGovernance(
        trail="T06",
        evidence_type=EvidenceType.PADRAO_ESTRUTURAL,
        role=EvidenceRole.NUCLEO,
        primary_unit="UG_ANO",
        convergence_core=True,
    ),
    "T07": TrailGovernance(
        trail="T07",
        evidence_type=EvidenceType.PADRAO_COMPORTAMENTAL,
        role=EvidenceRole.NUCLEO,
        primary_unit="UG_PORTADOR_ANO",
        convergence_core=True,
    ),
    "T08": TrailGovernance(
        trail="T08",
        evidence_type=EvidenceType.SINAL_ESTATISTICO,
        role=EvidenceRole.CONTEXTO,
        primary_unit="UG_ANO",
        convergence_core=False,
    ),
    "T09": TrailGovernance(
        trail="T09",
        evidence_type=EvidenceType.CONTEXTO_NORMATIVO,
        role=EvidenceRole.CONTEXTO,
        primary_unit="TRANSACAO_CENARIO_NORMATIVO",
        convergence_core=False,
    ),
}


def governance_for_trail(trail_code: str) -> TrailGovernance:
    return TRAIL_GOVERNANCE[normalize_trail_code(trail_code)]


def evidence_type_for_trail(trail_code: str) -> EvidenceType:
    return governance_for_trail(trail_code).evidence_type


def evidence_role_for_trail(trail_code: str) -> EvidenceRole:
    return governance_for_trail(trail_code).role


def primary_unit_for_trail(trail_code: str) -> str:
    return governance_for_trail(trail_code).primary_unit


def contributes_to_core_convergence(trail_code: str) -> bool:
    return governance_for_trail(trail_code).convergence_core
