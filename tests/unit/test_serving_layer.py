from __future__ import annotations

import pandas as pd
import pytest

from cpgf.serving import (
    ServingRepository,
    persist_serving_tables,
    validate_serving_bundle,
)
from cpgf.serving.duckdb import validate_logical_name


def _sample_tables() -> dict[str, pd.DataFrame]:
    return {
        "matrix_supplier_year": pd.DataFrame(
            {
                "CODIGO_UG": ["000001", "000002"],
                "ANO": [2024, 2025],
                "T01": [1, 0],
                "F1": [1, 0],
            }
        ),
        "overlap_supplier_trails": pd.DataFrame(
            {
                "TRILHA_A": ["T01"],
                "TRILHA_B": ["T02"],
                "JACCARD": [0.25],
            }
        ),
    }


def test_persist_serving_tables_builds_parquet_manifest_and_duckdb(tmp_path):
    manifest = persist_serving_tables(
        _sample_tables(),
        tmp_path,
        source={"input_sha256": "fixture"},
        canonical_validation={"fixture": True},
    )

    assert manifest["serving_version"] == "1.5.0"
    assert len(manifest["tables"]) == 2
    assert (tmp_path / "serving_manifest.json").is_file()
    assert (tmp_path / "cpgf_serving.duckdb").is_file()

    validation = validate_serving_bundle(tmp_path)
    assert validation["status"] == "PASS"
    assert validation["catalog_pass"]


def test_serving_repository_reads_only_registered_logical_views(tmp_path):
    persist_serving_tables(_sample_tables(), tmp_path)
    repository = ServingRepository(tmp_path / "cpgf_serving.duckdb")

    assert repository.count("matrix_supplier_year") == 2
    assert "v_matrix_supplier_year" in repository.list_views()

    frame = repository.read("matrix_supplier_year", limit=1)
    assert len(frame) == 1
    assert list(frame.columns) == ["CODIGO_UG", "ANO", "T01", "F1"]

    with pytest.raises(KeyError):
        repository.read("nao_existe")


def test_validate_serving_bundle_detects_modified_parquet(tmp_path):
    manifest = persist_serving_tables(_sample_tables(), tmp_path)
    target = tmp_path / manifest["tables"][0]["path"]
    target.write_bytes(b"corrompido")

    validation = validate_serving_bundle(tmp_path)
    assert validation["status"] == "FAIL"
    assert not all(check["pass"] for check in validation["table_checks"])


@pytest.mark.parametrize(
    "value",
    ["matrix_supplier_year", "pca_ug_trails_loadings", "t01"],
)
def test_validate_logical_name_accepts_safe_names(value):
    assert validate_logical_name(value) == value


@pytest.mark.parametrize(
    "value",
    ["Matrix Supplier", "../arquivo", "x;drop table serving_catalog", "1inicio"],
)
def test_validate_logical_name_rejects_unsafe_identifiers(value):
    with pytest.raises(ValueError):
        validate_logical_name(value)
