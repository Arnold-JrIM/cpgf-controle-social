from __future__ import annotations

import argparse
from pathlib import Path

from cpgf.serving import build_serving_bundle, validate_serving_bundle
from cpgf.settings.paths import SERVING_DIR


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Materializa a camada Parquet/DuckDB de serving do CPGF."
    )
    parser.add_argument("--input", type=Path, required=True, help="CSV CPGF de origem.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=SERVING_DIR,
        help="Diretório do bundle de serving.",
    )
    parser.add_argument(
        "--allow-noncanonical",
        action="store_true",
        help="Permite build fora do snapshot congelado. Não usar para publicação.",
    )
    args = parser.parse_args()

    manifest = build_serving_bundle(
        args.input,
        args.output_dir,
        require_canonical=not args.allow_noncanonical,
    )
    print(f"Serving version: {manifest['serving_version']}")
    print(f"Bundle: {args.output_dir}")
    print(f"Tabelas: {len(manifest['tables'])}")
    print(f"Catálogo: {manifest['catalog']['path']}")
    validation = validate_serving_bundle(args.output_dir)
    print(f"Validação do bundle: {validation['status']}")
    if validation["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
