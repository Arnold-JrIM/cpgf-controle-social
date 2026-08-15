from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pandas as pd

from cpgf.knowledge import (
    LexicalKnowledgeRetriever,
    build_knowledge_bundle,
    format_knowledge_citation,
    validate_knowledge_bundle,
)


def _write_synthetic_catalog(root: Path) -> tuple[Path, Path]:
    sources = root / "sources"
    sources.mkdir(parents=True)
    (sources / "norma.md").write_text(
        "Suprimento de fundos é acompanhado pelo ordenador de despesas. "
        "A prestação de contas documenta a aplicação dos recursos.",
        encoding="utf-8",
    )
    (sources / "artigo.txt").write_text(
        "Auditoria pública orientada por dados utiliza análise para identificar padrões e anomalias, "
        "preservando julgamento profissional.",
        encoding="utf-8",
    )
    catalog = root / "catalog.json"
    catalog.write_text(
        json.dumps(
            {
                "documents": [
                    {
                        "document_id": "norma-smoke",
                        "title": "Norma Smoke",
                        "source_class": "normative",
                        "authority_level": "primary_normative",
                        "distribution_policy": "public_official",
                        "expected_filename": "norma.md",
                        "authors": ["Órgão Público"],
                        "year": 2024,
                        "citation": "ÓRGÃO PÚBLICO. Norma Smoke. 2024.",
                        "trails": ["T03"],
                    },
                    {
                        "document_id": "artigo-smoke",
                        "title": "Artigo Smoke",
                        "source_class": "scientific",
                        "authority_level": "scientific_peer_reviewed",
                        "distribution_policy": "metadata_only",
                        "expected_filename": "artigo.txt",
                        "authors": ["Autor Teste"],
                        "year": 2025,
                        "citation": "AUTOR TESTE. Artigo Smoke. 2025.",
                    },
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return catalog, sources


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="cpgf-knowledge-smoke-") as temporary:
        root = Path(temporary)

        seed_sources = root / "seed-empty-sources"
        seed_sources.mkdir()
        seed_bundle = root / "seed-bundle"
        seed_manifest = build_knowledge_bundle(
            Path("data/knowledge/source_catalog.json"),
            seed_sources,
            seed_bundle,
        )
        seed_validation = validate_knowledge_bundle(seed_bundle)
        if seed_manifest["documents"] != 7:
            raise RuntimeError("Catálogo semente não possui sete documentos")
        if seed_manifest["documents_available"] != 0 or seed_manifest["chunks"] != 0:
            raise RuntimeError("Build metadata-only do catálogo semente divergiu do esperado")
        if seed_validation["status"] != "PASS":
            raise RuntimeError(f"Bundle metadata-only inválido: {seed_validation}")

        catalog, sources = _write_synthetic_catalog(root)
        bundle = root / "synthetic-bundle"
        manifest = build_knowledge_bundle(
            catalog,
            sources,
            bundle,
            require_all_sources=True,
            max_chars=600,
            overlap_chars=60,
        )
        validation = validate_knowledge_bundle(bundle)
        if validation["status"] != "PASS":
            raise RuntimeError(f"Bundle sintético inválido: {validation}")

        chunks = pd.read_parquet(bundle / "chunks.parquet")
        retriever = LexicalKnowledgeRetriever(chunks)
        hits = retriever.search("suprimento fundos prestação contas", limit=2)
        if not hits or hits[0].document_id != "norma-smoke":
            raise RuntimeError("Retriever lexical não priorizou a fonte normativa esperada")

        print("KNOWLEDGE SMOKE: PASS")
        print(f"Seed catalog documents: {seed_manifest['documents']}")
        print(f"Seed metadata-only: {seed_manifest['documents_metadata_only']}")
        print(f"Synthetic documents: {manifest['documents']}")
        print(f"Synthetic chunks: {manifest['chunks']}")
        print(f"Top hit: {hits[0].document_id}")
        print(f"Citation: {format_knowledge_citation(hits[0])}")
        print("Embeddings: DISABLED")
        print("LLM: DISABLED")


if __name__ == "__main__":
    main()
