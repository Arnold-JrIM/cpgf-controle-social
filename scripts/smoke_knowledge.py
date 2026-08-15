from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pandas as pd
from streamlit.testing.v1 import AppTest

from cpgf.knowledge import (
    LexicalKnowledgeRetriever,
    build_knowledge_bundle,
    load_source_catalog,
    validate_knowledge_bundle,
)


def _synthetic_catalog(root: Path) -> tuple[Path, Path]:
    sources = root / "sources"
    (sources / "normas").mkdir(parents=True)
    (sources / "artigos").mkdir()
    (sources / "historico").mkdir()
    (sources / "normas" / "norma.md").write_text(
        "Suprimento de fundos exige prestação de contas e observância dos limites aplicáveis.", encoding="utf-8"
    )
    (sources / "artigos" / "artigo.txt").write_text(
        "Auditoria orientada por dados apoia a seleção de sinais para análise humana.", encoding="utf-8"
    )
    (sources / "historico" / "lei.txt").write_text(
        "Esta regra histórica foi revogada e serve somente à interpretação temporal.", encoding="utf-8"
    )
    catalog_dir = root / "catalog"
    catalog_dir.mkdir()
    (catalog_dir / "core.json").write_text(
        json.dumps({"documents": [
            {"document_id":"norma-smoke","title":"Norma Smoke","source_class":"normative","authority_level":"primary_normative","distribution_policy":"public_official","expected_path":"normas/norma.md","citation":"ÓRGÃO. Norma Smoke.","supports_trails":["T03"]},
            {"document_id":"artigo-smoke","title":"Artigo Smoke","source_class":"scientific","authority_level":"scientific_peer_reviewed","distribution_policy":"metadata_only","expected_path":"artigos/artigo.txt","citation":"AUTOR. Artigo Smoke.","scope":"methodology","temporal_status":"contextual"}
        ]}, ensure_ascii=False), encoding="utf-8"
    )
    (catalog_dir / "historical.json").write_text(
        json.dumps({"documents": [
            {"document_id":"historico-smoke","title":"Histórico Smoke","source_class":"normative","authority_level":"primary_normative","distribution_policy":"public_official","expected_path":"historico/lei.txt","citation":"ÓRGÃO. Histórico Smoke.","scope":"historical","temporal_status":"historical","retrieval_default":False}
        ]}, ensure_ascii=False), encoding="utf-8"
    )
    index = root / "source_catalog.json"
    index.write_text(json.dumps({"includes":["catalog/core.json","catalog/historical.json"]}), encoding="utf-8")
    return index, sources


def main() -> None:
    seed = load_source_catalog(Path("data/knowledge/source_catalog.json"))
    if len(seed) != 45:
        raise RuntimeError(f"Corpus governado divergente: {len(seed)} documentos")
    if sum(item.retrieval_default for item in seed) != 35:
        raise RuntimeError("Quantidade de documentos de recuperação padrão divergiu")

    with tempfile.TemporaryDirectory(prefix="cpgf-knowledge-1-1-smoke-") as temporary:
        root = Path(temporary)
        empty_sources = root / "empty"
        empty_sources.mkdir()
        seed_bundle = root / "seed"
        seed_manifest = build_knowledge_bundle(Path("data/knowledge/source_catalog.json"), empty_sources, seed_bundle)
        if seed_manifest["documents"] != 45 or seed_manifest["documents_metadata_only"] != 45:
            raise RuntimeError("Build metadata-only do corpus governado divergiu")
        if validate_knowledge_bundle(seed_bundle)["status"] != "PASS":
            raise RuntimeError("Bundle metadata-only inválido")

        catalog, sources = _synthetic_catalog(root)
        bundle = root / "synthetic"
        manifest = build_knowledge_bundle(
            catalog, sources, bundle, require_all_sources=True, require_text_sources=True, max_chars=600, overlap_chars=60
        )
        if validate_knowledge_bundle(bundle)["status"] != "PASS":
            raise RuntimeError("Bundle sintético inválido")
        chunks = pd.read_parquet(bundle / "chunks.parquet")
        retriever = LexicalKnowledgeRetriever(chunks)
        hits = retriever.search("suprimento fundos prestação contas", limit=3)
        if not hits or hits[0].document_id != "norma-smoke":
            raise RuntimeError("Retriever não priorizou a norma esperada")
        if retriever.search("regra histórica revogada", limit=3):
            raise RuntimeError("Fonte histórica entrou na recuperação padrão")
        historical = retriever.search("regra histórica revogada", limit=3, include_non_default=True)
        if not historical or historical[0].document_id != "historico-smoke":
            raise RuntimeError("Opt-in histórico não funcionou")

        app = AppTest.from_file(str(Path("pages/07_Assistente_IA.py").resolve()))
        app.run(timeout=30)
        if app.exception:
            raise RuntimeError(f"Página Assistente IA falhou: {app.exception}")

        print("KNOWLEDGE 1.1.0 SMOKE: PASS")
        print(f"Catalog documents: {len(seed)}")
        print(f"Default retrieval documents: {sum(item.retrieval_default for item in seed)}")
        print(f"Synthetic documents: {manifest['documents']}")
        print(f"Synthetic chunks: {manifest['chunks']}")
        print("Historical default exclusion: PASS")
        print("Assistant page: PASS")
        print("Embeddings: DISABLED")
        print("LLM: DISABLED")


if __name__ == "__main__":
    main()
