from __future__ import annotations

import argparse
from pathlib import Path

from cpgf.knowledge import build_knowledge_bundle, validate_knowledge_bundle


def main() -> None:
    parser = argparse.ArgumentParser(description="Constrói o bundle local Knowledge 1.0.0.")
    parser.add_argument(
        "--catalog",
        type=Path,
        default=Path("data/knowledge/source_catalog.json"),
    )
    parser.add_argument(
        "--source-root",
        type=Path,
        default=Path("data/knowledge/sources"),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/knowledge/processed"),
    )
    parser.add_argument("--require-all-sources", action="store_true")
    args = parser.parse_args()

    manifest = build_knowledge_bundle(
        args.catalog,
        args.source_root,
        args.output_dir,
        require_all_sources=args.require_all_sources,
    )
    print(f"Knowledge version: {manifest['knowledge_version']}")
    print(f"Documentos: {manifest['documents']}")
    print(f"Documentos disponíveis: {manifest['documents_available']}")
    print(f"Chunks: {manifest['chunks']}")
    validation = validate_knowledge_bundle(args.output_dir)
    print(f"Validação: {validation['status']}")
    if validation["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
