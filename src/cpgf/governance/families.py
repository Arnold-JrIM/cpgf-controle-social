from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EvidenceFamily:
    code: str
    name: str
    trails: tuple[str, ...]


FAMILIES: dict[str, EvidenceFamily] = {
    "F1": EvidenceFamily(
        code="F1",
        name="Conformidade operacional observável",
        trails=("T01", "T02"),
    ),
    "F2": EvidenceFamily(
        code="F2",
        name="Repetição e recorrência de aquisições",
        trails=("T03", "T04", "T05"),
    ),
    "F3": EvidenceFamily(
        code="F3",
        name="Estrutura e concentração de fornecedor",
        trails=("T06",),
    ),
    "F4": EvidenceFamily(
        code="F4",
        name="Comportamento de saque",
        trails=("T07",),
    ),
    "F5": EvidenceFamily(
        code="F5",
        name="Contexto estatístico forense",
        trails=("T08",),
    ),
    "F6": EvidenceFamily(
        code="F6",
        name="Contexto normativo-financeiro",
        trails=("T09",),
    ),
}

TRAIL_TO_FAMILY: dict[str, str] = {
    trail: family.code
    for family in FAMILIES.values()
    for trail in family.trails
}


def normalize_trail_code(trail_code: str) -> str:
    code = str(trail_code).strip().upper()
    if code not in TRAIL_TO_FAMILY:
        raise ValueError(f"Trilha desconhecida para governança: {trail_code!r}")
    return code


def family_code_for_trail(trail_code: str) -> str:
    return TRAIL_TO_FAMILY[normalize_trail_code(trail_code)]


def family_for_trail(trail_code: str) -> EvidenceFamily:
    return FAMILIES[family_code_for_trail(trail_code)]


def family_name_for_trail(trail_code: str) -> str:
    return family_for_trail(trail_code).name


def family_catalog() -> tuple[EvidenceFamily, ...]:
    return tuple(FAMILIES[code] for code in sorted(FAMILIES))
