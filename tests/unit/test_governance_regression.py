import json

import pandas as pd

from cpgf.governance.governance_contract import (
    canonical_mapping_sha256,
    portable_governance_contract,
    validate_governance_bootstrap_report,
)
from cpgf.governance.governance_regression import (
    compare_governance_contract,
    dataframe_signature,
)


def test_dataframe_signature_is_stable_and_sensitive_to_content():
    frame = pd.DataFrame(
        {
            "A": [2, 1],
            "B": [0.12345678901234, 0.5],
        }
    )
    first = dataframe_signature(frame, sort_by=("A",))
    second = dataframe_signature(frame.iloc[::-1], sort_by=("A",))
    changed = dataframe_signature(frame.assign(B=[0.2, 0.5]), sort_by=("A",))

    assert first == second
    assert first["sha256"] != changed["sha256"]
    assert first["rows"] == 2


def test_dataframe_signature_can_freeze_only_contract_columns():
    frame = pd.DataFrame(
        {
            "ID": ["A", "B"],
            "FLAG": [1, 0],
            "DESCRICAO_NAO_CONTRATUAL": ["x", "y"],
        }
    )
    base = dataframe_signature(frame, columns=("ID", "FLAG"), sort_by=("ID",))
    changed = dataframe_signature(
        frame.assign(DESCRICAO_NAO_CONTRATUAL=["alterado", "tambem"]),
        columns=("ID", "FLAG"),
        sort_by=("ID",),
    )
    assert base == changed


def test_compare_governance_contract_reports_missing_and_changed_fields():
    observed = {"a": 1, "b": {"x": 2}}
    expected = {"a": 1, "b": {"x": 3}, "c": 4}

    checks = compare_governance_contract(observed, expected)
    by_field = {row["field"]: row for row in checks}

    assert by_field["a"]["pass"]
    assert not by_field["b"]["pass"]
    assert by_field["c"]["actual"] is None
    assert not by_field["c"]["pass"]


def test_canonical_mapping_sha256_is_order_independent_for_mapping_keys():
    first = canonical_mapping_sha256({"b": 2, "a": {"y": 1, "x": 0}})
    second = canonical_mapping_sha256({"a": {"x": 0, "y": 1}, "b": 2})
    changed = canonical_mapping_sha256({"a": {"x": 0, "y": 2}, "b": 2})

    assert first == second
    assert first != changed


def _portable_fixture() -> dict[str, object]:
    return {
        "rows": 10,
        "signatures": {
            "matrix_ug_year": {
                "rows": 10,
                "columns": ["UG", "T01"],
                "sha256": "matrix-exact",
            },
            "pca_ug_trails_loadings": {
                "rows": 12,
                "columns": ["REGRA", "COMPONENTE", "CARGA"],
                "sha256": "eigen-run-a",
            },
            "multicollinearity_ug_trails_condition": {
                "rows": 3,
                "columns": ["COMPONENTE", "AUTOVALOR", "INDICE_CONDICAO"],
                "sha256": "condition-run-a",
            },
        },
    }


def test_portable_contract_ignores_only_eigendecomposition_value_hashes():
    observed = _portable_fixture()
    base = canonical_mapping_sha256(portable_governance_contract(observed))

    changed_eigen_hashes = _portable_fixture()
    changed_eigen_hashes["signatures"]["pca_ug_trails_loadings"]["sha256"] = "eigen-run-b"
    changed_eigen_hashes["signatures"]["multicollinearity_ug_trails_condition"][
        "sha256"
    ] = "condition-run-b"
    assert canonical_mapping_sha256(portable_governance_contract(changed_eigen_hashes)) == base

    changed_shape = _portable_fixture()
    changed_shape["signatures"]["pca_ug_trails_loadings"]["rows"] = 13
    assert canonical_mapping_sha256(portable_governance_contract(changed_shape)) != base

    changed_deterministic_hash = _portable_fixture()
    changed_deterministic_hash["signatures"]["matrix_ug_year"]["sha256"] = "changed"
    assert canonical_mapping_sha256(portable_governance_contract(changed_deterministic_hash)) != base


def test_validate_governance_bootstrap_report_requires_bootstrap_and_portable_digest(tmp_path):
    observed = _portable_fixture()
    expected_digest = canonical_mapping_sha256(portable_governance_contract(observed))
    contract = tmp_path / "contract.json"
    contract.write_text(
        json.dumps({"expected_portable_contract_sha256": expected_digest}),
        encoding="utf-8",
    )

    passed = validate_governance_bootstrap_report(
        {"status": "BOOTSTRAP_PASS", "observed_contract": observed},
        contract,
    )

    changed_eigen_only = _portable_fixture()
    changed_eigen_only["signatures"]["pca_ug_trails_loadings"]["sha256"] = "other-run"
    still_passed = validate_governance_bootstrap_report(
        {"status": "BOOTSTRAP_PASS", "observed_contract": changed_eigen_only},
        contract,
    )

    changed_matrix = _portable_fixture()
    changed_matrix["signatures"]["matrix_ug_year"]["sha256"] = "other-matrix"
    failed = validate_governance_bootstrap_report(
        {"status": "BOOTSTRAP_PASS", "observed_contract": changed_matrix},
        contract,
    )

    assert passed["status"] == "PASS"
    assert passed["digest_pass"]
    assert still_passed["status"] == "PASS"
    assert failed["status"] == "FAIL"
    assert not failed["digest_pass"]
