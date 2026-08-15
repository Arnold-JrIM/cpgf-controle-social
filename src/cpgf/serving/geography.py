from __future__ import annotations

import json
from pathlib import Path

from cpgf.geography.aggregates import build_geographic_aggregates, validate_geographic_baseline
from cpgf.geography.ug_dimension import (
    GEO_VERSION,
    build_ug_geographic_dimension,
    sha256_file as geo_sha256_file,
    validate_cpgf_geographic_coverage,
)
from cpgf.governance.governance_regression import _primary_outputs
from cpgf.governance.matrices import build_diagnostic_matrices
from cpgf.governance.regression import sha256_file
from cpgf.preprocessing.build_staging import build_staging_from_csv
from cpgf.serving.duckdb import build_duckdb_catalog
from cpgf.serving.materialize import (
    build_diagnostic_serving_tables,
    persist_serving_tables,
    validate_canonical_serving_inputs,
)
from cpgf.version import MOTOR_VERSION, PREPARATION_VERSION, RULES_VERSION, SERVING_VERSION


def _complete(frame):
    if "STATUS_PERIODO" not in frame.columns:
        raise ValueError("Matriz diagnóstica sem STATUS_PERIODO.")
    return frame.loc[frame["STATUS_PERIODO"].eq("COMPLETO")].copy().reset_index(drop=True)


def _kind(name: str) -> str:
    if name.startswith("matrix_"):
        return "matrix"
    if name.startswith("dim_"):
        return "dimension"
    if name.startswith("geo_"):
        return "geography"
    return "diagnostic"


def build_serving_bundle_with_geography(
    input_path: Path,
    siafi_input_path: Path,
    output_dir: Path,
    *,
    require_canonical: bool = True,
    contract_path: Path | None = None,
) -> dict[str, object]:
    """Constrói o Serving 1.5.0, incorporando a Geo 1.1.0 sem alterar o motor."""
    input_path = Path(input_path)
    siafi_input_path = Path(siafi_input_path)
    output_dir = Path(output_dir)

    staged = build_staging_from_csv(input_path)
    primary_outputs = _primary_outputs(staged)
    matrices = build_diagnostic_matrices(staged, primary_outputs)
    supplier = matrices["supplier_year"].copy()
    ug = matrices["ug_year"].copy()
    supplier_complete = _complete(supplier)
    ug_complete = _complete(ug)

    validation: dict[str, object] = {}
    if require_canonical:
        validation = validate_canonical_serving_inputs(
            input_path,
            supplier_complete,
            ug_complete,
            contract_path=contract_path,
        )

    dimension = build_ug_geographic_dimension(
        siafi_input_path,
        require_frozen_source=require_canonical,
    )
    geographic_coverage = validate_cpgf_geographic_coverage(staged, dimension)
    geographic_tables = build_geographic_aggregates(staged, dimension)
    geographic_baseline = (
        validate_geographic_baseline(geographic_tables) if require_canonical else {}
    )

    tables = {
        "matrix_supplier_year": supplier,
        "matrix_ug_year": ug,
        **build_diagnostic_serving_tables(supplier_complete, ug_complete),
        "dim_ug_geografica": dimension,
        **geographic_tables,
    }
    manifest = persist_serving_tables(
        tables,
        output_dir,
        source={
            "input_path": str(input_path),
            "input_sha256": sha256_file(input_path),
            "input_rows": int(len(staged)),
            "siafi_input_path": str(siafi_input_path),
            "siafi_input_sha256": geo_sha256_file(siafi_input_path),
            "complete_years_only_in_diagnostics": True,
        },
        canonical_validation=validation,
        build_catalog=False,
    )

    for item in manifest["tables"]:
        item["kind"] = _kind(str(item["name"]))
    manifest["versions"] = {
        "preparation": PREPARATION_VERSION,
        "rules": RULES_VERSION,
        "motor": MOTOR_VERSION,
        "geo": GEO_VERSION,
        "serving": SERVING_VERSION,
    }
    manifest["geography"] = {
        "interpretation": (
            "UF_UG representa a localização cadastral da Unidade Gestora; "
            "não representa necessariamente o local físico da transação."
        ),
        "coverage": geographic_coverage,
        "baseline_validation": geographic_baseline,
        "temporal_references": {
            "TRANSACAO": "ANO_TRANSACAO; somente DATA TRANSAÇÃO observável",
            "EXTRATO": "ANO_EXTRATO_REF; cobertura pelo ciclo do extrato",
        },
        "no_hybrid_year": True,
    }

    manifest_path = output_dir / "serving_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    catalog_path = output_dir / "cpgf_serving.duckdb"
    build_duckdb_catalog(output_dir, manifest_path, catalog_path)
    manifest["catalog"] = {
        "path": catalog_path.relative_to(output_dir).as_posix(),
        "sha256": sha256_file(catalog_path),
        "bytes": int(catalog_path.stat().st_size),
    }
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return manifest
