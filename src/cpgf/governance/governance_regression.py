from __future__ import annotations

import gc
import hashlib
import json
from collections.abc import Mapping
from pathlib import Path
from time import perf_counter

import pandas as pd

from cpgf.preprocessing.build_staging import build_staging_from_csv
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
from cpgf.version import MOTOR_VERSION, PREPARATION_VERSION, RULES_VERSION

from .exposure import (
    BASELINE_COMPLETE_SUPPLIER_YEAR_N,
    BASELINE_COMPLETE_UG_YEAR_N,
    COMPLETE_YEAR_END,
    COMPLETE_YEAR_START,
)
from .marginality import (
    marginal_by_annual_decile,
    marginal_by_supplier_exposure,
    marginal_contribution,
)
from .matrices import SUPPLIER_CORE_TRAILS, UG_CORE_TRAILS, build_diagnostic_matrices
from .multicollinearity import multicollinearity_by_group, multicollinearity_diagnostics
from .overlap import (
    pairwise_binary_metrics,
    pairwise_by_annual_decile,
    pairwise_by_supplier_exposure,
    pairwise_by_year,
)
from .pca import pca_by_group, principal_component_diagnostics
from .regression import load_regression_contract, sha256_file

SUPPLIER_FAMILIES: tuple[str, ...] = ("F1", "F2", "F3")
UG_FAMILIES: tuple[str, ...] = ("F1", "F2", "F3", "F4")

SUPPLIER_MATRIX_SIGNATURE_COLUMNS: tuple[str, ...] = (
    "CODIGO_UG",
    "CHAVE_ENTIDADE",
    "ANO",
    "BANDA_EXPOSICAO_FORNECEDOR",
    *SUPPLIER_CORE_TRAILS,
    *SUPPLIER_FAMILIES,
    "T08_CONTEXTO",
    "T09_CONTEXTO",
)
UG_MATRIX_SIGNATURE_COLUMNS: tuple[str, ...] = (
    "CODIGO_UG",
    "ANO",
    "DECIL_EXPOSICAO_ANUAL",
    *UG_CORE_TRAILS,
    *UG_FAMILIES,
    "T08_CONTEXTO",
    "T09_CONTEXTO",
)


class _DigestWriter:
    def __init__(self) -> None:
        self.digest = hashlib.sha256()

    def write(self, text: str) -> int:
        self.digest.update(text.encode("utf-8"))
        return len(text)


def dataframe_signature(
    frame: pd.DataFrame,
    *,
    columns: tuple[str, ...] | None = None,
    sort_by: tuple[str, ...] | None = None,
) -> dict[str, object]:
    """Assina uma tabela de forma reprodutível sem persistir seus registros."""
    selected = frame.copy() if columns is None else frame.loc[:, list(columns)].copy()
    if sort_by:
        selected = selected.sort_values(list(sort_by), kind="stable").reset_index(drop=True)
    float_columns = selected.select_dtypes(include="floating").columns
    if len(float_columns):
        selected.loc[:, float_columns] = selected.loc[:, float_columns].round(12)

    writer = _DigestWriter()
    selected.to_csv(
        writer,
        index=False,
        lineterminator="\n",
        na_rep="<NA>",
        float_format="%.12g",
    )
    return {
        "rows": int(len(selected)),
        "columns": list(selected.columns),
        "sha256": writer.digest.hexdigest(),
    }


def compare_governance_contract(
    observed: Mapping[str, object],
    expected: Mapping[str, object],
) -> list[dict[str, object]]:
    """Compara os campos congelados sem tolerância ou descarte silencioso."""
    return [
        {
            "field": key,
            "expected": expected.get(key),
            "actual": observed.get(key),
            "pass": observed.get(key) == expected.get(key),
        }
        for key in sorted(set(observed) | set(expected))
    ]


def _primary_outputs(staged: pd.DataFrame) -> dict[str, pd.DataFrame]:
    indicators = compute_benford_ug_year(staged)
    ranked = rank_relative_benford(indicators) if not indicators.empty else pd.DataFrame()
    return {
        "T01": detect_weekend_purchases(staged),
        "T02": detect_installment_transactions(staged),
        "T03": detect_exact_repetition_groups(staged, portador_column="PORTADOR_ID"),
        "T04": detect_multi_cardholder_groups(staged, portador_column="PORTADOR_ID"),
        "T05": detect_vendor_recurrence_episodes(staged, portador_column="PORTADOR_ID"),
        "T06": detect_vendor_concentration_signals(staged),
        "T07": detect_withdrawal_recurrence_signals(staged, portador_column="PORTADOR_ID"),
        "T08": build_benford_signals(ranked),
        "T09": detect_limit_context_signals(staged),
    }


def _complete(frame: pd.DataFrame) -> pd.DataFrame:
    if "STATUS_PERIODO" not in frame.columns:
        raise ValueError("Matriz diagnóstica sem STATUS_PERIODO.")
    return frame.loc[frame["STATUS_PERIODO"].eq("COMPLETO")].copy().reset_index(drop=True)


def _positive_counts(frame: pd.DataFrame, flags: tuple[str, ...]) -> dict[str, int]:
    return {flag: int(frame[flag].fillna(0).astype(int).sum()) for flag in flags}


def _sign(
    registry: dict[str, dict[str, object]],
    name: str,
    frame: pd.DataFrame,
    *,
    columns: tuple[str, ...] | None = None,
    sort_by: tuple[str, ...] | None = None,
) -> None:
    registry[name] = dataframe_signature(frame, columns=columns, sort_by=sort_by)


def _diagnostic_signatures(
    supplier: pd.DataFrame,
    ug: pd.DataFrame,
) -> dict[str, dict[str, object]]:
    signatures: dict[str, dict[str, object]] = {}

    _sign(
        signatures,
        "matrix_supplier_year",
        supplier,
        columns=SUPPLIER_MATRIX_SIGNATURE_COLUMNS,
        sort_by=("ANO", "CODIGO_UG", "CHAVE_ENTIDADE"),
    )
    _sign(
        signatures,
        "matrix_ug_year",
        ug,
        columns=UG_MATRIX_SIGNATURE_COLUMNS,
        sort_by=("ANO", "CODIGO_UG"),
    )

    tables = {
        "overlap_supplier_trails": pairwise_binary_metrics(
            supplier, SUPPLIER_CORE_TRAILS, "UG_FORNECEDOR_ANO"
        ),
        "overlap_supplier_families": pairwise_binary_metrics(
            supplier, SUPPLIER_FAMILIES, "UG_FORNECEDOR_ANO"
        ),
        "overlap_ug_trails": pairwise_binary_metrics(ug, UG_CORE_TRAILS, "UG_ANO"),
        "overlap_ug_families": pairwise_binary_metrics(ug, UG_FAMILIES, "UG_ANO"),
        "overlap_supplier_trails_by_year": pairwise_by_year(
            supplier, SUPPLIER_CORE_TRAILS, "UG_FORNECEDOR_ANO"
        ),
        "overlap_ug_trails_by_year": pairwise_by_year(ug, UG_CORE_TRAILS, "UG_ANO"),
        "overlap_supplier_trails_by_exposure": pairwise_by_supplier_exposure(
            supplier, SUPPLIER_CORE_TRAILS
        ),
        "overlap_supplier_families_by_exposure": pairwise_by_supplier_exposure(
            supplier, SUPPLIER_FAMILIES
        ),
        "overlap_ug_trails_by_decile": pairwise_by_annual_decile(ug, UG_CORE_TRAILS),
        "overlap_ug_families_by_decile": pairwise_by_annual_decile(ug, UG_FAMILIES),
        "marginal_supplier_trails": marginal_contribution(
            supplier, SUPPLIER_CORE_TRAILS, "UG_FORNECEDOR_ANO"
        ),
        "marginal_supplier_families": marginal_contribution(
            supplier, SUPPLIER_FAMILIES, "UG_FORNECEDOR_ANO", kind="FAMILIA"
        ),
        "marginal_ug_trails": marginal_contribution(ug, UG_CORE_TRAILS, "UG_ANO"),
        "marginal_ug_families": marginal_contribution(
            ug, UG_FAMILIES, "UG_ANO", kind="FAMILIA"
        ),
        "marginal_supplier_trails_by_exposure": marginal_by_supplier_exposure(
            supplier, SUPPLIER_CORE_TRAILS
        ),
        "marginal_supplier_families_by_exposure": marginal_by_supplier_exposure(
            supplier, SUPPLIER_FAMILIES
        ),
        "marginal_ug_trails_by_decile": marginal_by_annual_decile(ug, UG_CORE_TRAILS),
        "marginal_ug_families_by_decile": marginal_by_annual_decile(ug, UG_FAMILIES),
    }

    for prefix, frame, trails, families, unit, group_column in (
        (
            "supplier",
            supplier,
            SUPPLIER_CORE_TRAILS,
            SUPPLIER_FAMILIES,
            "UG_FORNECEDOR_ANO",
            "BANDA_EXPOSICAO_FORNECEDOR",
        ),
        (
            "ug",
            ug,
            UG_CORE_TRAILS,
            UG_FAMILIES,
            "UG_ANO",
            "DECIL_EXPOSICAO_ANUAL",
        ),
    ):
        for kind_name, variables, kind in (
            ("trails", trails, "TRILHA"),
            ("families", families, "FAMILIA"),
        ):
            multi = multicollinearity_diagnostics(frame, variables, unit, kind=kind)
            multi_group = multicollinearity_by_group(
                frame, variables, unit, group_column, kind=kind
            )
            pca = principal_component_diagnostics(frame, variables, unit, kind=kind)
            pca_group = pca_by_group(frame, variables, unit, group_column, kind=kind)

            for name, table in multi.items():
                tables[f"multicollinearity_{prefix}_{kind_name}_{name}"] = table
            for name, table in multi_group.items():
                tables[
                    f"multicollinearity_{prefix}_{kind_name}_{name}_by_exposure"
                ] = table
            for name, table in pca.items():
                tables[f"pca_{prefix}_{kind_name}_{name}"] = table
            for name, table in pca_group.items():
                tables[f"pca_{prefix}_{kind_name}_{name}_by_exposure"] = table

    for name, table in tables.items():
        _sign(signatures, name, table)
    return dict(sorted(signatures.items()))


def run_governance_regression(
    input_path: Path,
    *,
    contract_path: Path | None = None,
    bootstrap: bool = False,
) -> dict[str, object]:
    """Executa o gate integral da Governança 1.3.2 sobre o snapshot canônico."""
    input_path = Path(input_path)
    trail_contract = load_regression_contract()
    expected_sha = str(trail_contract["baseline_sha256"])
    actual_sha = sha256_file(input_path)
    if actual_sha != expected_sha:
        raise ValueError(
            "A regressão da Governança 1.3.2 exige o snapshot canônico. "
            f"Esperado={expected_sha}; obtido={actual_sha}."
        )

    started = perf_counter()
    staged = build_staging_from_csv(input_path)
    staging_seconds = perf_counter() - started
    raw_rows = int(len(staged))

    started = perf_counter()
    outputs = _primary_outputs(staged)
    trails_seconds = perf_counter() - started
    primary_counts = {code: int(len(table)) for code, table in sorted(outputs.items())}

    production_counts = trail_contract["production_counts"]
    if not isinstance(production_counts, Mapping):
        raise TypeError("Contrato T01–T09 inválido em production_counts.")
    expected_primary = {str(code): int(value) for code, value in production_counts.items()}
    primary_checks = [
        {
            "trail": code,
            "expected": expected_primary.get(code),
            "actual": primary_counts.get(code),
            "pass": primary_counts.get(code) == expected_primary.get(code),
        }
        for code in sorted(set(primary_counts) | set(expected_primary))
    ]

    started = perf_counter()
    matrices = build_diagnostic_matrices(staged, outputs)
    matrices_seconds = perf_counter() - started
    supplier = _complete(matrices["supplier_year"])
    ug = _complete(matrices["ug_year"])
    del matrices, staged, outputs
    gc.collect()

    structural_checks = [
        {
            "field": "supplier_year_rows_complete",
            "expected": BASELINE_COMPLETE_SUPPLIER_YEAR_N,
            "actual": int(len(supplier)),
            "pass": len(supplier) == BASELINE_COMPLETE_SUPPLIER_YEAR_N,
        },
        {
            "field": "ug_year_rows_complete",
            "expected": BASELINE_COMPLETE_UG_YEAR_N,
            "actual": int(len(ug)),
            "pass": len(ug) == BASELINE_COMPLETE_UG_YEAR_N,
        },
    ]

    started = perf_counter()
    signatures = _diagnostic_signatures(supplier, ug)
    diagnostics_seconds = perf_counter() - started

    observed_contract = {
        "raw_rows": raw_rows,
        "input_sha256": actual_sha,
        "complete_year_start": COMPLETE_YEAR_START,
        "complete_year_end": COMPLETE_YEAR_END,
        "primary_counts": primary_counts,
        "supplier_year_rows_complete": int(len(supplier)),
        "ug_year_rows_complete": int(len(ug)),
        "supplier_positive_counts": _positive_counts(
            supplier, (*SUPPLIER_CORE_TRAILS, *SUPPLIER_FAMILIES)
        ),
        "ug_positive_counts": _positive_counts(ug, (*UG_CORE_TRAILS, *UG_FAMILIES)),
        "signatures": signatures,
    }

    all_base_checks = all(check["pass"] for check in primary_checks + structural_checks)
    contract_checks: list[dict[str, object]] = []
    if bootstrap:
        status = "BOOTSTRAP_PASS" if all_base_checks else "FAIL"
    else:
        if contract_path is None:
            contract_path = (
                Path(__file__).resolve().parents[3]
                / "data"
                / "manifests"
                / "governance_regression_1_3_2.json"
            )
        payload = json.loads(Path(contract_path).read_text(encoding="utf-8"))
        expected = payload["expected_contract"]
        contract_checks = compare_governance_contract(observed_contract, expected)
        status = (
            "PASS"
            if all_base_checks and all(check["pass"] for check in contract_checks)
            else "FAIL"
        )

    return {
        "status": status,
        "bootstrap": bootstrap,
        "canonical_input": True,
        "input": {
            "path": str(input_path),
            "rows": raw_rows,
            "sha256": actual_sha,
        },
        "versions": {
            "preparation": PREPARATION_VERSION,
            "rules": RULES_VERSION,
            "motor": MOTOR_VERSION,
        },
        "scope": {
            "complete_year_start": COMPLETE_YEAR_START,
            "complete_year_end": COMPLETE_YEAR_END,
            "partial_periods_excluded_from_diagnostics": True,
        },
        "timing_seconds": {
            "staging": round(staging_seconds, 3),
            "trails": round(trails_seconds, 3),
            "matrices": round(matrices_seconds, 3),
            "diagnostics": round(diagnostics_seconds, 3),
        },
        "primary_checks": primary_checks,
        "structural_checks": structural_checks,
        "contract_checks": contract_checks,
        "observed_contract": observed_contract,
    }


def write_governance_regression_report(
    report: Mapping[str, object],
    output_path: Path,
) -> Path:
    """Persiste o relatório sem incluir dados transacionais brutos."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, default=str) + "\n",
        encoding="utf-8",
    )
    return output_path
