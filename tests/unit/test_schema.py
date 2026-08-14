import pandas as pd
import pytest

from cpgf.ingestion.validators import CPGF_REFERENCE_COLUMNS
from cpgf.preprocessing.schema import SchemaError, inspect_columns, validate_raw_frame


def test_schema_accepts_reference_columns_and_optional_provenance():
    columns = [*CPGF_REFERENCE_COLUMNS, "COMPETENCIA_ARQUIVO", "ARQUIVO_ORIGEM"]
    inspection = inspect_columns(columns)
    assert inspection.valid
    assert inspection.extra_columns == ("COMPETENCIA_ARQUIVO", "ARQUIVO_ORIGEM")


def test_schema_rejects_missing_required_column():
    frame = pd.DataFrame(columns=list(CPGF_REFERENCE_COLUMNS[:-1]))
    with pytest.raises(SchemaError, match="VALOR TRANSAÇÃO"):
        validate_raw_frame(frame)
