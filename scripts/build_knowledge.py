from __future__ import annotations

import argparse
from pathlib import Path

from cpgf.knowledge import build_knowledge_bundle, validate_knowledge_bundle
from cpgf.version import KNOWLEDGE_VERSION


def main() -> None:
    parser = argparse.ArgumentParser(description=f"Constrói o bundle local Knowledge {KNOWLEDGE_VERSION}.")
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
    parser.add_argument(
        "--require-text-sources",
        action="store_true",
        help="Falha se uma fonte de recuperação padrão estiver disponível, mas sem texto extraível.",
    )
    parser.add_argument(
        "--no-verify-source-contract",
        action="store_true",
        help="Desabilita somente para diagnóstico a checagem de hash/tamanho/páginas congelados no catálogo.",
    )
    args = parser.parse_args()

    manifest = build_knowledge_bundle(
        args.catalog,
        args.source_root,
        args.output_dir,
        require_all_sources=args.require_all_sources,
        require_text_sources=args.require_text_sources,
        verify_source_contract=not args.no_verify_source_contract,
    )
    print(f"Knowledge version: {manifest['knowledge_version']}")
    print(f"Documentos: {manifest['documents']}")
    print(f"Documentos disponíveis: {manifest['documents_available']}")
    print(f"Documentos metadata-only: {manifest['documents_metadata_only']}")
    print(f"Documentos disponíveis não ingeridos: {manifest['documents_available_not_ingested']}")
    print(f"Chunks: {manifest['chunks']}")
    print(f"Chunks de recuperação padrão: {manifest['chunks_retrieval_default']}")
    validation = validate_knowledge_bundle(args.output_dir)
    print(f"Validação: {validation['status']}")
    if validation["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
