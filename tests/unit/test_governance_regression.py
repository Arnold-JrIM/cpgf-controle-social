import json

import pandas as pd

from cpgf.governance.governance_contract import (
    canonical_mapping_sha256,
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


def test_validate_governance_bootstrap_report_requires_bootstrap_and_digest(tmp_path):
    observed = {"rows": 10, "signatures": {"matrix": "abc"}}
    expected_digest = canonical_mapping_sha256(observed)
    contract = tmp_path / "contract.json"
    contract.write_text(
        json.dumps({"expected_observed_contract_sha256": expected_digest}),
        encoding="utf-8",
    )

    passed = validate_governance_bootstrap_report(
        {"status": "BOOTSTRAP_PASS", "observed_contract": observed},
        contract,
    )
    failed = validate_governance_bootstrap_report(
        {"status": "BOOTSTRAP_PASS", "observed_contract": {"rows": 11}},
        contract,
    )

    assert passed["status"] == "PASS"
    assert passed["digest_pass"]
    assert failed["status"] == "FAIL"
    assert not failed["digest_pass"]
