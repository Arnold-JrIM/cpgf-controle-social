from __future__ import annotations

import argparse
from pathlib import Path

from cpgf.preprocessing.build_staging import build_staging_from_csv


def main() -> None:
    parser = argparse.ArgumentParser(description="Constrói staging CPGF da Preparação 1.1.0.")
    parser.add_argument("--input", type=Path, required=True, help="CSV CPGF bruto ou consolidado.")
    parser.add_argument("--output", type=Path, required=True, help="Parquet de staging a gerar.")
    args = parser.parse_args()

    staged = build_staging_from_csv(args.input, args.output)
    print(f"Staging gerado: {args.output}")
    print(f"Registros: {len(staged):,}")
    print(f"Colunas: {len(staged.columns)}")


if __name__ == "__main__":
    main()
