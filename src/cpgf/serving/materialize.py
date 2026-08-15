from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping

import pandas as pd

from cpgf.governance.governance_regression import (
    SUPPLIER_FAMILIES,
    SUPPLIER_MATRIX_SIGNATURE_COLUMNS,
    UG_FAMILIES,
    UG_MATRIX_SIGNATURE_COLUMNS,
    _primary_outputs,
    dataframe_signature,
)
from cpgf.governance.marginality import (
    marginal_by_annual_decile,
    marginal_by_supplier_exposure,
    marginal_contribution,
)
from cpgf.governance.matrices import (
    SUPPLIER_CORE_TRAILS,
    UG_CORE_TRAILS,
    build_diagnostic_matrices,
)
from cpgf.governance.multicollinearity import (
    multicollinearity_by_group,
    multicollinearity_diagnostics,
)
from cpgf.governance.overlap import (
    pairwise_binary_metrics,
    pairwise_by_annual_decile,
    pairwise_by_supplier_exposure,
    pairwise_by_year,
)
from cpgf.governance.pca import pca_by_group, principal_component_diagnostics
from cpgf.governance.regression import sha256_file
from cpgf.preprocessing.build_staging import build_staging_from_csv
from cpgf.settings.paths import MANIFEST_DIR
from cpgf.version import MOTOR_VERSION, PREPARATION_VERSION, RULES_VERSION, SERVING_VERSION

from .duckdb import build_duckdb_catalog, open_catalog


def _complete(frame: pd.DataFrame) -> pd.DataFrame:
    if "STATUS_PERIODO" not in frame.columns:
        raise ValueError("Matriz diagnóstica sem STATUS_PERIODO.")
    return frame.loc[frame["STATUS_PERIODO"].eq("COMPLETO")].copy().reset_index(drop=True)


def build_diagnostic_serving_tables(
    supplier_complete: pd.DataFrame,
    ug_complete: pd.DataFrame,
) -> dict[str, pd.DataFrame]:
    """Reproduz as tabelas diagnósticas congeladas no Motor 1.3.2."""
    tables: dict[str, pd.DataFrame] = {
        "overlap_supplier_trails": pairwise_binary_metrics(
            supplier_complete, SUPPLIER_CORE_TRAILS, "UG_FORNECEDOR_ANO"
        ),
        "overlap_supplier_families": pairwise_binary_metrics(
            supplier_complete, SUPPLIER_FAMILIES, "UG_FORNECEDOR_ANO"
        ),
        "overlap_ug_trails": pairwise_binary_metrics(
            ug_complete, UG_CORE_TRAILS, "UG_ANO"
        ),
        "overlap_ug_families": pairwise_binary_metrics(
            ug_complete, UG_FAMILIES, "UG_ANO"
        ),
        "overlap_supplier_trails_by_year": pairwise_by_year(
            supplier_complete, SUPPLIER_CORE_TRAILS, "UG_FORNECEDOR_ANO"
        ),
        "overlap_ug_trails_by_year": pairwise_by_year(
            ug_complete, UG_CORE_TRAILS, "UG_ANO"
        ),
        "overlap_supplier_trails_by_exposure": pairwise_by_supplier_exposure(
            supplier_complete, SUPPLIER_CORE_TRAILS
        ),
        "overlap_supplier_families_by_exposure": pairwise_by_supplier_exposure(
            supplier_complete, SUPPLIER_FAMILIES
        ),
        "overlap_ug_trails_by_decile": pairwise_by_annual_decile(
            ug_complete, UG_CORE_TRAILS
        ),
        "overlap_ug_families_by_decile": pairwise_by_annual_decile(
            ug_complete, UG_FAMILIES
        ),
        "marginal_supplier_trails": marginal_contribution(
            supplier_complete, SUPPLIER_CORE_TRAILS, "UG_FORNECEDOR_ANO"
        ),
        "marginal_supplier_families": marginal_contribution(
            supplier_complete,
            SUPPLIER_FAMILIES,
            "UG_FORNECEDOR_ANO",
            kind="FAMILIA",
        ),
        "marginal_ug_trails": marginal_contribution(
            ug_complete, UG_CORE_TRAILS, "UG_ANO"
        ),
        "marginal_ug_families": marginal_contribution(
            ug_complete, UG_FAMILIES, "UG_ANO", kind="FAMILIA"
        ),
        "marginal_supplier_trails_by_exposure": marginal_by_supplier_exposure(
            supplier_complete, SUPPLIER_CORE_TRAILS
        ),
        "marginal_supplier_families_by_exposure": marginal_by_supplier_exposure(
            supplier_complete, SUPPLIER_FAMILIES
        ),
        "marginal_ug_trails_by_decile": marginal_by_annual_decile(
            ug_complete, UG_CORE_TRAILS
        ),
        "marginal_ug_families_by_decile": marginal_by_annual_decile(
            ug_complete, UG_FAMILIES
        ),
    }

    for prefix, frame, trails, families, unit, group_column in (
        (
            "supplier",
            supplier_complete,
            SUPPLIER_CORE_TRAILS,
            SUPPLIER_FAMILIES,
            "UG_FORNECEDOR_ANO",
            "BANDA_EXPOSICAO_FORNECEDOR",
        ),
        (
            "ug",
            ug_complete,
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

    return dict(sorted(tables.items()))


def _canonical_governance_contract(path: Path | None = None) -> dict[str, object]:
    contract_path = path or (MANIFEST_DIR / "governance_regression_1_3_2.json")
    return json.loads(Path(contract_path).read_text(encoding="utf-8"))


def validate_canonical_serving_inputs(
    input_path: Path,
    supplier_complete: pd.DataFrame,
    ug_complete: pd.DataFrame,
    *,
    contract_path: Path | None = None,
) -> dict[str, object]:
    """Valida que as matrizes a servir reproduzem o contrato canônico do PR #19."""
    contract = _canonical_governance_contract(contract_path)
    canonical_input = contract["canonical_input"]
    if not isinstance(canonical_input, Mapping):
        raise TypeError("Manifesto de governança inválido em canonical_input.")

    expected_input_sha = str(canonical_input["sha256"])
    actual_input_sha = sha256_file(input_path)
    if actual_input_sha != expected_input_sha:
        raise ValueError(
            "A camada canônica de serving exige o snapshot congelado. "
            f"Esperado={expected_input_sha}; obtido={actual_input_sha}."
        )

    universes = contract["universes"]
    signatures = contract["matrix_signatures"]
    if not isinstance(universes, Mapping) or not isinstance(signatures, Mapping):
        raise TypeError("Manifesto de governança sem universes/matrix_signatures válidos.")

    supplier_signature = dataframe_signature(
        supplier_complete,
        columns=SUPPLIER_MATRIX_SIGNATURE_COLUMNS,
        sort_by=("ANO", "CODIGO_UG", "CHAVE_ENTIDADE"),
    )
    ug_signature = dataframe_signature(
        ug_complete,
        columns=UG_MATRIX_SIGNATURE_COLUMNS,
        sort_by=("ANO", "CODIGO_UG"),
    )

    checks = {
        "input_sha256": actual_input_sha,
        "supplier_year_rows": int(len(supplier_complete)),
        "ug_year_rows": int(len(ug_complete)),
        "supplier_year_signature": supplier_signature["sha256"],
        "ug_year_signature": ug_signature["sha256"],
    }
    expected = {
        "supplier_year_rows": int(universes["supplier_year"]),
        "ug_year_rows": int(universes["ug_year"]),
        "supplier_year_signature": str(signatures["supplier_year"]),
        "ug_year_signature": str(signatures["ug_year"]),
    }
    failed = {
        field: {"expected": expected[field], "actual": checks[field]}
        for field in expected
        if checks[field] != expected[field]
    }
    if failed:
        raise ValueError(f"Matrizes de serving divergiram do contrato canônico: {failed}")
    return checks


def _table_artifact(
    name: str,
    frame: pd.DataFrame,
    parquet_path: Path,
    *,
    kind: str,
    root: Path,
) -> dict[str, object]:
    parquet_path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(parquet_path, index=False, compression="zstd")
    return {
        "name": name,
        "kind": kind,
        "path": parquet_path.relative_to(root).as_posix(),
        "rows": int(len(frame)),
        "columns": [str(column) for column in frame.columns],
        "sha256": sha256_file(parquet_path),
        "bytes": int(parquet_path.stat().st_size),
    }


def persist_serving_tables(
    tables: Mapping[str, pd.DataFrame],
    output_dir: Path,
    *,
    source: Mapping[str, object] | None = None,
    canonical_validation: Mapping[str, object] | None = None,
    build_catalog: bool = True,
) -> dict[str, object]:
    """Materializa DataFrames curados em Parquet, manifesto e catálogo DuckDB."""
    output_dir = Path(output_dir)
    parquet_dir = output_dir / "parquet"
    parquet_dir.mkdir(parents=True, exist_ok=True)

    artifacts: list[dict[str, object]] = []
    for name, frame in sorted(tables.items()):
        kind = "matrix" if name.startswith("matrix_") else "diagnostic"
        artifacts.append(
            _table_artifact(
                name,
                frame,
                parquet_dir / f"{name}.parquet",
                kind=kind,
                root=output_dir,
            )
        )

    manifest: dict[str, object] = {
        "serving_version": SERVING_VERSION,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "versions": {
            "preparation": PREPARATION_VERSION,
            "rules": RULES_VERSION,
            "motor": MOTOR_VERSION,
            "serving": SERVING_VERSION,
        },
        "source": dict(source or {}),
        "canonical_validation": dict(canonical_validation or {}),
        "tables": artifacts,
    }
    manifest_path = output_dir / "serving_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    if build_catalog:
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


def validate_serving_bundle(output_dir: Path) -> dict[str, object]:
    """Valida hashes, schemas, cardinalidades e catálogo do bundle materializado."""
    output_dir = Path(output_dir)
    manifest_path = output_dir / "serving_manifest.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(f"Manifesto de serving inexistente: {manifest_path}")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    tables = manifest.get("tables", [])
    if not isinstance(tables, list) or not tables:
        raise ValueError("Manifesto de serving sem tables válidas.")

    checks: list[dict[str, object]] = []
    for item in tables:
        if not isinstance(item, dict):
            raise TypeError("Entrada inválida em tables do manifesto de serving.")
        parquet_path = output_dir / str(item["path"])
        exists = parquet_path.is_file()
        actual_sha = sha256_file(parquet_path) if exists else None
        read_ok = False
        frame = pd.DataFrame()
        if exists:
            try:
                frame = pd.read_parquet(parquet_path)
                read_ok = True
            except Exception:
                read_ok = False
        actual_rows = int(len(frame)) if read_ok else None
        actual_columns = [str(column) for column in frame.columns] if read_ok else []
        passed = (
            exists
            and read_ok
            and actual_sha == str(item["sha256"])
            and actual_rows == int(item["rows"])
            and actual_columns == [str(column) for column in item["columns"]]
        )
        checks.append(
            {
                "name": str(item["name"]),
                "exists": exists,
                "read_pass": read_ok,
                "sha256_pass": actual_sha == str(item["sha256"]) if exists else False,
                "rows_pass": actual_rows == int(item["rows"]) if read_ok else False,
                "columns_pass": (
                    actual_columns == [str(column) for column in item["columns"]]
                    if read_ok
                    else False
                ),
                "pass": passed,
            }
        )

    catalog = manifest.get("catalog")
    catalog_pass = False
    if isinstance(catalog, Mapping):
        catalog_path = output_dir / str(catalog["path"])
        if catalog_path.is_file() and sha256_file(catalog_path) == str(catalog["sha256"]):
            connection = open_catalog(catalog_path)
            try:
                catalog_rows = int(
                    connection.execute("SELECT COUNT(*) FROM serving_catalog").fetchone()[0]
                )
            finally:
                connection.close()
            catalog_pass = catalog_rows == len(tables)

    status = "PASS" if all(check["pass"] for check in checks) and catalog_pass else "FAIL"
    return {
        "status": status,
        "table_checks": checks,
        "catalog_pass": catalog_pass,
        "table_count": len(tables),
    }


def build_serving_bundle(
    input_path: Path,
    output_dir: Path,
    *,
    require_canonical: bool = True,
    contract_path: Path | None = None,
) -> dict[str, object]:
    """Constrói o bundle Parquet/DuckDB a partir do CSV CPGF."""
    input_path = Path(input_path)
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

    tables: dict[str, pd.DataFrame] = {
        "matrix_supplier_year": supplier,
        "matrix_ug_year": ug,
    }
    tables.update(build_diagnostic_serving_tables(supplier_complete, ug_complete))

    return persist_serving_tables(
        tables,
        output_dir,
        source={
            "input_path": str(input_path),
            "input_sha256": sha256_file(input_path),
            "input_rows": int(len(staged)),
            "complete_years_only_in_diagnostics": True,
        },
        canonical_validation=validation,
    )
