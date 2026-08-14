from __future__ import annotations

import argparse
from pathlib import Path

from cpgf.ingestion.cpgf import PortalBlocked, PortalReturnedHTML, update_incremental
from cpgf.ingestion.manifests import load_manifest, write_manifest_atomic
from cpgf.settings.paths import MANIFEST_DIR, OUTPUT_DIR, RAW_DIR


def main() -> None:
    parser = argparse.ArgumentParser(description="Atualiza competências do CPGF após a baseline.")
    parser.add_argument("--last-known", default=None)
    parser.add_argument("--raw-dir", type=Path, default=RAW_DIR / "cpgf")
    parser.add_argument("--max-new", type=int, default=12)
    parser.add_argument("--pause-min", type=float, default=25.0)
    parser.add_argument("--pause-max", type=float, default=45.0)
    args = parser.parse_args()

    baseline = load_manifest(MANIFEST_DIR / "cpgf.json")
    last_known = args.last_known or baseline["competence_end"]
    output_manifest = OUTPUT_DIR / "ingestion" / "cpgf_update_manifest.json"

    try:
        results = update_incremental(
            last_known,
            args.raw_dir,
            max_new_competences=args.max_new,
            min_pause_seconds=args.pause_min,
            max_pause_seconds=args.pause_max,
        )
    except (PortalBlocked, PortalReturnedHTML) as exc:
        raise SystemExit(
            "Atualização interrompida de forma segura por proteção do Portal. "
            f"Nenhum manifest canônico foi alterado. Detalhe: {exc}"
        ) from exc

    payload = {
        "baseline_competence_end": baseline["competence_end"],
        "requested_last_known": last_known,
        "downloaded_competencies": [result.competence for result in results],
        "files": [result.file_metadata for result in results],
    }
    write_manifest_atomic(output_manifest, payload)

    if results:
        print(f"Novas competências válidas: {', '.join(payload['downloaded_competencies'])}")
    else:
        print("Nenhuma nova competência foi encontrada.")
    print(f"Relatório local: {output_manifest}")


if __name__ == "__main__":
    main()
