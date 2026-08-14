from __future__ import annotations

import argparse
from pathlib import Path

from cpgf.ingestion.manifests import write_manifest_atomic
from cpgf.ingestion.siafi import discover_latest_csv_resource, download_resource
from cpgf.settings.paths import OUTPUT_DIR, RAW_DIR


def main() -> None:
    parser = argparse.ArgumentParser(description="Baixa o recurso CSV mais recente do cadastro de UGs SIAFI.")
    parser.add_argument("--destination", type=Path, default=RAW_DIR / "siafi" / "siafi_dados_ug_latest.csv")
    args = parser.parse_args()

    resource = discover_latest_csv_resource()
    metadata = download_resource(resource, args.destination)
    manifest = OUTPUT_DIR / "ingestion" / "siafi_update_manifest.json"
    write_manifest_atomic(manifest, metadata)

    print(f"Recurso CKAN: {resource.name}")
    print(f"Arquivo: {args.destination}")
    print(f"Relatório local: {manifest}")


if __name__ == "__main__":
    main()
