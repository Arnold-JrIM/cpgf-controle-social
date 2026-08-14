import pandas as pd
import pytest

from cpgf.governance import (
    AUTOMATIC_CONFIRMED,
    EvidenceRole,
    EvidenceType,
    ValidationStatus,
    consolidate_evidence,
    contributes_to_core_convergence,
    evidence_type_for_trail,
    family_code_for_trail,
    family_for_trail,
    normalize_validation_status,
    tag_evidence,
)
from cpgf.version import MOTOR_VERSION, PREPARATION_VERSION, RULES_VERSION


def test_frozen_family_catalog_maps_t01_t09():
    expected = {
        "T01": "F1",
        "T02": "F1",
        "T03": "F2",
        "T04": "F2",
        "T05": "F2",
        "T06": "F3",
        "T07": "F4",
        "T08": "F5",
        "T09": "F6",
    }

    assert {trail: family_code_for_trail(trail) for trail in expected} == expected
    assert family_for_trail("T05").name == "Repetição e recorrência de aquisições"


def test_evidence_taxonomy_keeps_context_outside_core_convergence():
    assert evidence_type_for_trail("T01") == EvidenceType.FATO_DETERMINISTICO
    assert evidence_type_for_trail("T06") == EvidenceType.PADRAO_ESTRUTURAL
    assert evidence_type_for_trail("T08") == EvidenceType.SINAL_ESTATISTICO
    assert evidence_type_for_trail("T09") == EvidenceType.CONTEXTO_NORMATIVO

    assert contributes_to_core_convergence("T01") is True
    assert contributes_to_core_convergence("T07") is True
    assert contributes_to_core_convergence("T08") is False
    assert contributes_to_core_convergence("T09") is False


def test_validation_protocol_never_auto_confirms():
    assert AUTOMATIC_CONFIRMED is False
    assert normalize_validation_status("confirmado") == ValidationStatus.CONFIRMADO

    with pytest.raises(ValueError, match="STATUS_VALIDACAO inválido"):
        normalize_validation_status("IRREGULAR")


def test_tag_evidence_preserves_cardinality_and_adds_governance_contract():
    frame = pd.DataFrame(
        {
            "ID_SINAL": ["T01_a", "T01_b"],
            "UG_ID": ["1", "2"],
            "NIVEL_TRIAGEM": ["ATENCAO", "ATENCAO"],
        }
    )

    tagged = tag_evidence(frame, "t01")

    assert len(tagged) == len(frame)
    assert tagged["ID_EVIDENCIA"].tolist() == ["T01_a", "T01_b"]
    assert tagged["TRILHA"].eq("T01").all()
    assert tagged["FAMILIA_EVIDENCIA"].eq("F1").all()
    assert tagged["TIPO_EVIDENCIA"].eq(EvidenceType.FATO_DETERMINISTICO.value).all()
    assert tagged["PAPEL_EVIDENCIA"].eq(EvidenceRole.NUCLEO.value).all()
    assert tagged["CONVERGENCIA_NUCLEO"].all()
    assert tagged["STATUS_VALIDACAO"].eq(ValidationStatus.NAO_VALIDADO.value).all()
    assert tagged["VERSAO_PREPARACAO"].eq(PREPARATION_VERSION).all()
    assert tagged["VERSAO_REGRAS"].eq(RULES_VERSION).all()
    assert tagged["VERSAO_MOTOR"].eq(MOTOR_VERSION).all()


def test_tag_evidence_rejects_duplicate_primary_ids():
    frame = pd.DataFrame({"ID_SINAL": ["dup", "dup"]})

    with pytest.raises(ValueError, match="ID_EVIDENCIA deve ser único"):
        tag_evidence(frame, "T03")


def test_consolidation_does_not_merge_or_deduplicate_different_trails():
    frames = {
        "T01": pd.DataFrame({"ID_SINAL": ["same"], "NIVEL_TRIAGEM": ["ATENCAO"]}),
        "T09": pd.DataFrame({"ID_SINAL": ["same"], "NIVEL_TRIAGEM": ["INFORMATIVO"]}),
    }

    result = consolidate_evidence(frames)

    assert len(result) == 2
    assert result["TRILHA"].tolist() == ["T01", "T09"]
    assert result["CONVERGENCIA_NUCLEO"].tolist() == [True, False]
    assert result["FAMILIA_EVIDENCIA"].tolist() == ["F1", "F6"]
