from pathlib import Path

import pytest

from cpgf.ingestion.validators import (
    competence_range,
    next_competence,
    validate_competence,
    validate_cpgf_header,
)


def test_competence_helpers():
    assert validate_competence("202607") is True
    assert validate_competence("202613") is False
    assert next_competence("202612") == "202701"
    assert competence_range("202611", "202702") == ["202611", "202612", "202701", "202702"]


def test_invalid_competence_raises():
    with pytest.raises(ValueError):
        next_competence("202699")


def test_cpgf_header_fixture_is_valid():
    fixture = Path(__file__).parents[2] / "data" / "fixtures" / "cpgf_minimal.csv"
    result = validate_cpgf_header(fixture)

    assert result["valid"] is True
    assert result["same_reference_set"] is True
    assert result["same_reference_order"] is True
