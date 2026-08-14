from __future__ import annotations

import argparse

from cpgf.ingestion.cpgf import download_range
from cpgf.ingestion.kaggle import download_snapshot
from cpgf.ingestion.siafi import discover_latest_csv_resource, download_resource
from cpgf.settings.paths import RAW_DIR


def main() -> None:
    parser = argparse.ArgumentParser(description="Obtém dados para reprodução do projeto CPGF.")
    parser.add_argument("--source", choices=("kaggle", "official"), required=True)
    parser.add_argument("--start", default=None, help="Competência inicial AAAAMM no modo official.")
    parser.add_argument("--end", default=None, help="Competência final AAAAMM no modo official.")
    parser.add_argument("--pause-min", type=float, default=25.0)
    parser.add_argument("--pause-max", type=float, default=45.0)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    if args.source == "kaggle":
        target = RAW_DIR / "kaggle_snapshot"
        resolved = download_snapshot(target, force_download=args.force)
        print(f"Snapshot Kaggle disponível em: {resolved}")
        return

    if not args.start or not args.end:
        raise SystemExit(
            "No modo official, informe explicitamente --start AAAAMM e --end AAAAMM. "
            "Isso evita iniciar acidentalmente uma extração histórica extensa."
        )

    cpgf_dir = RAW_DIR / "cpgf"
    results = download_range(
        args.start,
        args.end,
        cpgf_dir,
        min_pause_seconds=args.pause_min,
        max_pause_seconds=args.pause_max,
    )
    print(f"CPGF: {len(results)} competência(s) conferida(s) em {cpgf_dir}")

    resource = discover_latest_csv_resource()
    siafi_path = RAW_DIR / "siafi" / "siafi_dados_ug_latest.csv"
    download_resource(resource, siafi_path)
    print(f"SIAFI: {siafi_path}")


if __name__ == "__main__":
    main()
