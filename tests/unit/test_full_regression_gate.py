from __future__ import annotations

from pathlib import Path

import pandas as pd

import cpgf.governance.regression as regression


def _frame(size: int) -> pd.DataFrame:
    return pd.DataFrame({"row": range(size)})


def test_contract_preserves_historical_and_production_t07_counts():
    contract = regression.load_regression_contract()

    assert contract["baseline_sha256"] == (
        "300789f9bd866f313df4ca5ee5dfca7234050ef2452443b61b1e58425ca0997b"
    )
    assert contract["baseline_counts"]["T07"] == 1089
    assert contract["production_counts"]["T07"] == 1088
    assert contract["baseline_counts"]["T08"] == 12
    assert contract["baseline_counts"]["T09"] == 46941


def test_compare_counts_exposes_delta_and_missing_trails():
    checks = regression.compare_counts(
        {"T01": 10, "T02": 2},
        {"T01": 10, "T02": 3, "T03": 1},
    )

    by_trail = {check["trail"]: check for check in checks}
    assert by_trail["T01"]["pass"] is True
    assert by_trail["T01"]["delta"] == 0
    assert by_trail["T02"]["pass"] is False
    assert by_trail["T02"]["delta"] == -1
    assert by_trail["T03"]["actual"] is None
    assert by_trail["T03"]["pass"] is False


def test_sha256_file_uses_file_bytes(tmp_path: Path):
    sample = tmp_path / "sample.csv"
    sample.write_bytes(b"abc")

    assert regression.sha256_file(sample) == (
        "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    )


def test_collect_trail_counts_replays_both_cardholder_identities(monkeypatch):
    seen_columns: dict[str, list[str]] = {code: [] for code in ("T03", "T04", "T05", "T07")}

    monkeypatch.setattr(regression, "detect_weekend_purchases", lambda staged: _frame(1))
    monkeypatch.setattr(regression, "detect_installment_transactions", lambda staged: _frame(2))
    monkeypatch.setattr(
        regression, "detect_vendor_concentration_signals", lambda staged: _frame(6)
    )
    monkeypatch.setattr(regression, "detect_limit_context_signals", lambda staged: _frame(9))
    monkeypatch.setattr(regression, "compute_benford_ug_year", lambda staged: _frame(80))
    monkeypatch.setattr(regression, "rank_relative_benford", lambda frame: frame)
    monkeypatch.setattr(regression, "build_benford_signals", lambda frame: _frame(8))

    def fake_identity(code: str, size: int):
        def operation(staged, *, portador_column):
            seen_columns[code].append(portador_column)
            return _frame(size)

        return operation

    monkeypatch.setattr(regression, "detect_exact_repetition_groups", fake_identity("T03", 3))
    monkeypatch.setattr(regression, "detect_multi_cardholder_groups", fake_identity("T04", 4))
    monkeypatch.setattr(regression, "detect_vendor_recurrence_episodes", fake_identity("T05", 5))
    monkeypatch.setattr(
        regression, "detect_withdrawal_recurrence_signals", fake_identity("T07", 7)
    )

    measured = regression.collect_trail_counts(
        pd.DataFrame(), modes=("baseline", "production")
    )

    assert measured["baseline"]["counts"] == {
        "T01": 1,
        "T02": 2,
        "T03": 3,
        "T04": 4,
        "T05": 5,
        "T06": 6,
        "T07": 7,
        "T08": 8,
        "T09": 9,
    }
    assert measured["production"]["counts"] == measured["baseline"]["counts"]
    for code in seen_columns:
        assert seen_columns[code] == ["PORTADOR_ID_BASELINE", "PORTADOR_ID"]
