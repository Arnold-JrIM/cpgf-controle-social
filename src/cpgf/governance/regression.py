from __future__ import annotations

import gc
import hashlib
import json
from collections.abc import Callable, Iterable, Mapping
from pathlib import Path
from time import perf_counter
from typing import Literal

import pandas as pd
import yaml

from cpgf.preprocessing.build_staging import build_staging_from_csv
from cpgf.settings.paths import CONFIG_DIR
from cpgf.trails.t01_weekend import detect_weekend_purchases
from cpgf.trails.t02_installment import detect_installment_transactions
from cpgf.trails.t03_exact_repetition import detect_exact_repetition_groups
from cpgf.trails.t04_multi_cardholder import detect_multi_cardholder_groups
from cpgf.trails.t05_vendor_recurrence import detect_vendor_recurrence_episodes
from cpgf.trails.t06_vendor_concentration import detect_vendor_concentration_signals
from cpgf.trails.t07_withdrawals import detect_withdrawal_recurrence_signals
from cpgf.trails.t08_benford import (
    build_benford_signals,
    compute_benford_ug_year,
    rank_relative_benford,
)
from cpgf.trails.t09_limits import detect_limit_context_signals
from cpgf.version import (
    MOTOR_VERSION,
    PREPARATION_BASELINE_VERSION,
    PREPARATION_VERSION,
    RULES_VERSION,
)

RegressionMode = Literal["baseline", "production"]


def sha256_file(path: Path, *, chunk_size: int = 8 * 1024 * 1024) -> str:
    """Calcula SHA-256 em streaming para não carregar o arquivo inteiro em memória."""
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def load_regression_contract(path: Path | None = None) -> dict[str, object]:
    """Lê do catálogo versionado o hash e as contagens canônicas esperadas."""
    contract_path = CONFIG_DIR / "trails.yaml" if path is None else Path(path)
    payload = yaml.safe_load(contract_path.read_text(encoding="utf-8"))

    metadata = payload["metadata"]
    baseline = {
        str(code): int(value)
        for code, value in payload["baseline_regression"]["expected_counts"].items()
    }
    production = baseline.copy()
    production_overrides = payload.get("production_expectations", {}).get(
        "preparation_1_1_0", {}
    )
    for code, value in production_overrides.items():
        if str(code).startswith("T"):
            production[str(code)] = int(value)

    return {
        "baseline_sha256": str(metadata["baseline_sha256"]),
        "baseline_file": str(metadata["baseline_file"]),
        "baseline_counts": baseline,
        "production_counts": production,
    }


def compare_counts(
    actual: Mapping[str, int], expected: Mapping[str, int]
) -> list[dict[str, object]]:
    """Compara contagens por trilha sem ocultar diferenças nulas ou positivas."""
    codes = sorted(set(actual) | set(expected))
    checks: list[dict[str, object]] = []
    for code in codes:
        actual_value = actual.get(code)
        expected_value = expected.get(code)
        delta = (
            None
            if actual_value is None or expected_value is None
            else int(actual_value) - int(expected_value)
        )
        checks.append(
            {
                "trail": code,
                "expected": expected_value,
                "actual": actual_value,
                "delta": delta,
                "pass": actual_value == expected_value,
            }
        )
    return checks


def _measure_count(
    operation: Callable[[], pd.DataFrame],
) -> tuple[int, float]:
    started = perf_counter()
    frame = operation()
    count = int(len(frame))
    elapsed = perf_counter() - started
    del frame
    gc.collect()
    return count, elapsed


def _collect_common_counts(staged: pd.DataFrame) -> tuple[dict[str, int], dict[str, float]]:
    counts: dict[str, int] = {}
    elapsed: dict[str, float] = {}

    operations: list[tuple[str, Callable[[], pd.DataFrame]]] = [
        ("T01", lambda: detect_weekend_purchases(staged)),
        ("T02", lambda: detect_installment_transactions(staged)),
        ("T06", lambda: detect_vendor_concentration_signals(staged)),
        ("T09", lambda: detect_limit_context_signals(staged)),
    ]
    for code, operation in operations:
        counts[code], elapsed[code] = _measure_count(operation)

    def t08_signals() -> pd.DataFrame:
        indicators = compute_benford_ug_year(staged)
        ranked = rank_relative_benford(indicators) if not indicators.empty else pd.DataFrame()
        return build_benford_signals(ranked)

    counts["T08"], elapsed["T08"] = _measure_count(t08_signals)
    return counts, elapsed


def _collect_identity_counts(
    staged: pd.DataFrame,
    *,
    portador_column: str,
) -> tuple[dict[str, int], dict[str, float]]:
    counts: dict[str, int] = {}
    elapsed: dict[str, float] = {}
    operations: list[tuple[str, Callable[[], pd.DataFrame]]] = [
        (
            "T03",
            lambda: detect_exact_repetition_groups(
                staged, portador_column=portador_column
            ),
        ),
        (
            "T04",
            lambda: detect_multi_cardholder_groups(
                staged, portador_column=portador_column
            ),
        ),
        (
            "T05",
            lambda: detect_vendor_recurrence_episodes(
                staged, portador_column=portador_column
            ),
        ),
        (
            "T07",
            lambda: detect_withdrawal_recurrence_signals(
                staged, portador_column=portador_column
            ),
        ),
    ]
    for code, operation in operations:
        counts[code], elapsed[code] = _measure_count(operation)
    return counts, elapsed


def collect_trail_counts(
    staged: pd.DataFrame,
    *,
    modes: Iterable[RegressionMode] = ("baseline", "production"),
) -> dict[str, dict[str, object]]:
    """Executa T01–T09 e separa a identidade histórica da identidade de produção.

    T01, T02, T06, T08 e T09 não dependem da chave de portador e são executadas
    uma única vez. T03, T04, T05 e T07 são reexecutadas em cada modo para que a
    equivalência esperada — e a diferença conhecida de T07 — seja empiricamente
    observável no mesmo relatório.
    """
    requested = tuple(dict.fromkeys(modes))
    invalid = set(requested) - {"baseline", "production"}
    if invalid:
        raise ValueError(f"Modos de regressão inválidos: {sorted(invalid)}")

    common_counts, common_elapsed = _collect_common_counts(staged)
    results: dict[str, dict[str, object]] = {}
    for mode in requested:
        portador_column = (
            "PORTADOR_ID_BASELINE" if mode == "baseline" else "PORTADOR_ID"
        )
        identity_counts, identity_elapsed = _collect_identity_counts(
            staged,
            portador_column=portador_column,
        )
        counts = {**common_counts, **identity_counts}
        elapsed = {**common_elapsed, **identity_elapsed}
        results[mode] = {
            "portador_column": portador_column,
            "counts": dict(sorted(counts.items())),
            "elapsed_seconds": {
                code: round(value, 3) for code, value in sorted(elapsed.items())
            },
        }
    return results


def run_full_regression(
    input_path: Path,
    *,
    modes: Iterable[RegressionMode] = ("baseline", "production"),
    allow_other_hash: bool = False,
    contract_path: Path | None = None,
) -> dict[str, object]:
    """Executa o gate integral contra o contrato congelado de regressão."""
    input_path = Path(input_path)
    contract = load_regression_contract(contract_path)
    expected_sha = str(contract["baseline_sha256"])
    actual_sha = sha256_file(input_path)
    canonical_input = actual_sha == expected_sha

    if not canonical_input and not allow_other_hash:
        raise ValueError(
            "SHA-256 da base diverge do contrato congelado. "
            f"Esperado={expected_sha}; obtido={actual_sha}. "
            "Use --allow-other-hash apenas para diagnóstico não canônico."
        )

    staging_started = perf_counter()
    staged = build_staging_from_csv(input_path)
    staging_seconds = perf_counter() - staging_started
    raw_rows = int(len(staged))

    requested_modes = tuple(dict.fromkeys(modes))
    measured = collect_trail_counts(staged, modes=requested_modes)
    del staged
    gc.collect()

    results: dict[str, dict[str, object]] = {}
    all_checks_pass = True
    for mode in requested_modes:
        expected_key = "baseline_counts" if mode == "baseline" else "production_counts"
        expected = contract[expected_key]
        if not isinstance(expected, Mapping):
            raise TypeError(f"Contrato inválido em {expected_key}.")
        counts = measured[mode]["counts"]
        if not isinstance(counts, Mapping):
            raise TypeError(f"Medição inválida no modo {mode}.")
        checks = compare_counts(counts, expected)
        mode_pass = all(bool(check["pass"]) for check in checks)
        all_checks_pass = all_checks_pass and mode_pass
        results[mode] = {
            **measured[mode],
            "expected_counts": dict(sorted(expected.items())),
            "checks": checks,
            "pass": mode_pass,
        }

    if canonical_input:
        status = "PASS" if all_checks_pass else "FAIL"
    else:
        status = "DIAGNOSTIC_ONLY"

    return {
        "status": status,
        "canonical_input": canonical_input,
        "input": {
            "path": str(input_path),
            "rows": raw_rows,
            "sha256": actual_sha,
            "expected_sha256": expected_sha,
            "expected_filename": contract["baseline_file"],
        },
        "versions": {
            "preparation_baseline": PREPARATION_BASELINE_VERSION,
            "preparation_production": PREPARATION_VERSION,
            "rules": RULES_VERSION,
            "motor": MOTOR_VERSION,
        },
        "staging_seconds": round(staging_seconds, 3),
        "modes": results,
    }


def write_regression_report(report: Mapping[str, object], output_path: Path) -> Path:
    """Persiste o relatório sem incluir dados transacionais brutos."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, default=str) + "\n",
        encoding="utf-8",
    )
    return output_path
