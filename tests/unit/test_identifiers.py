from cpgf.preprocessing.identifiers import (
    PORTADOR_ID_BASELINE_VERSION,
    PORTADOR_ID_VERSION,
    build_portador_id,
    build_portador_id_baseline,
    normalize_digits,
    normalize_name,
    normalize_ug,
)


def test_identifier_versions():
    assert PORTADOR_ID_BASELINE_VERSION == "1.0.0"
    assert PORTADOR_ID_VERSION == "1.1.0"


def test_normalize_digits_masked_cpf():
    assert normalize_digits("***.123.***-**") == "123"
    assert normalize_digits("-1") is None
    assert normalize_digits("") is None


def test_normalize_name_is_deterministic():
    assert normalize_name("  João   da  Silva ") == "JOAO DA SILVA"
    assert normalize_name("JOÃO DA SILVA") == "JOAO DA SILVA"


def test_normalize_ug_as_six_digits():
    assert normalize_ug("133") == "000133"
    assert normalize_ug("000133") == "000133"


def test_baseline_portador_id_reproduces_masked_cpf_semantics():
    assert build_portador_id_baseline("***123***", "Pessoa A") == "123"
    assert build_portador_id_baseline("***123***", "Sigilo") is None


def test_v110_key_combines_ug_cpf_and_normalized_name():
    assert build_portador_id("133", "***123***", " João  da Silva ") == (
        "000133|123|JOAO DA SILVA"
    )


def test_same_person_formatting_produces_same_key():
    first = build_portador_id("000133", "***123***", "João da Silva")
    second = build_portador_id("133", "123", "  JOAO   DA SILVA ")
    assert first == second


def test_same_masked_cpf_different_names_in_same_ug_are_distinct():
    first = build_portador_id("000133", "***123***", "Pessoa A")
    second = build_portador_id("000133", "***123***", "Pessoa B")
    assert first != second


def test_same_masked_cpf_in_different_ugs_is_distinct():
    first = build_portador_id("000133", "***123***", "Pessoa A")
    second = build_portador_id("000134", "***123***", "Pessoa A")
    assert first != second


def test_missing_ug_or_cpf_does_not_create_identity():
    assert build_portador_id("", "***123***", "Pessoa A") is None
    assert build_portador_id("000133", "-1", "Pessoa A") is None
