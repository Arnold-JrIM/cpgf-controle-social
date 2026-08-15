from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from cpgf.knowledge import (
    LexicalKnowledgeRetriever,
    build_knowledge_bundle,
    format_knowledge_citation,
    load_source_catalog,
    validate_knowledge_bundle,
)
from cpgf.knowledge.models import DocumentSpec
from cpgf.knowledge.splitter import split_sections
from cpgf.knowledge.loader import load_document


def _catalog(tmp_path: Path) -> tuple[Path, Path]:
    source_root = tmp_path / "sources"
    source_root.mkdir()
    (source_root / "norma.md").write_text(
        "# Suprimento de fundos\n\nO ordenador acompanha a aplicação e a prestação de contas. "
        "O cartão é meio de pagamento do suprimento de fundos.",
        encoding="utf-8",
    )
    (source_root / "artigo.txt").write_text(
        "Auditoria pública orientada por dados pode usar inteligência artificial para apoiar "
        "a identificação de padrões e anomalias.",
        encoding="utf-8",
    )
    payload = {
        "documents": [
            {
                "document_id": "norma-teste",
                "title": "Norma de teste",
                "source_class": "normative",
                "authority_level": "primary_normative",
                "distribution_policy": "public_official",
                "expected_filename": "norma.md",
                "authors": ["Órgão Público"],
                "authority": "Órgão Público",
                "year": 2024,
                "publisher": "Órgão Público",
                "citation": "ÓRGÃO PÚBLICO. Norma de teste. 2024.",
                "trails": ["T03"],
                "active": True,
            },
            {
                "document_id": "artigo-teste",
                "title": "Artigo de teste",
                "source_class": "scientific",
                "authority_level": "scientific_peer_reviewed",
                "distribution_policy": "metadata_only",
                "expected_filename": "artigo.txt",
                "authors": ["Autor Um"],
                "year": 2025,
                "publisher": "Revista Teste",
                "citation": "AUTOR UM. Artigo de teste. 2025.",
                "trails": [],
                "active": True,
            },
        ]
    }
    catalog = tmp_path / "catalog.json"
    catalog.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return catalog, source_root


def test_seed_catalog_is_valid_and_has_expected_classes():
    catalog = load_source_catalog(Path("data/knowledge/source_catalog.json"))
    assert len(catalog) == 7
    assert any(item.authority_level.value == "primary_normative" for item in catalog)
    assert any(item.authority_level.value == "scientific_peer_reviewed" for item in catalog)
    assert any(item.distribution_policy.value == "metadata_only" for item in catalog)


def test_catalog_rejects_path_traversal():
    with pytest.raises(ValueError):
        DocumentSpec(
            document_id="doc-teste",
            title="Documento teste",
            source_class="scientific",
            authority_level="scientific_peer_reviewed",
            distribution_policy="metadata_only",
            expected_filename="../segredo.pdf",
            citation="Teste.",
        )


def test_build_and_validate_knowledge_bundle(tmp_path):
    catalog, source_root = _catalog(tmp_path)
    output = tmp_path / "bundle"
    manifest = build_knowledge_bundle(
        catalog,
        source_root,
        output,
        require_all_sources=True,
        max_chars=500,
        overlap_chars=50,
    )
    assert manifest["knowledge_version"] == "1.0.0"
    assert manifest["documents"] == 2
    assert manifest["documents_available"] == 2
    assert manifest["chunks"] == 2
    assert validate_knowledge_bundle(output)["status"] == "PASS"


def test_missing_source_is_explicit_metadata_only(tmp_path):
    catalog, source_root = _catalog(tmp_path)
    (source_root / "artigo.txt").unlink()
    output = tmp_path / "bundle"
    manifest = build_knowledge_bundle(catalog, source_root, output)
    assert manifest["documents_metadata_only"] == 1
    assert manifest["missing_sources"] == ["artigo-teste"]
    assert validate_knowledge_bundle(output)["status"] == "PASS"


def test_require_all_sources_fails_when_document_is_missing(tmp_path):
    catalog, source_root = _catalog(tmp_path)
    (source_root / "artigo.txt").unlink()
    with pytest.raises(FileNotFoundError):
        build_knowledge_bundle(catalog, source_root, tmp_path / "bundle", require_all_sources=True)


def test_lexical_retriever_returns_relevant_source_and_citation(tmp_path):
    catalog, source_root = _catalog(tmp_path)
    output = tmp_path / "bundle"
    build_knowledge_bundle(catalog, source_root, output, require_all_sources=True)
    chunks = pd.read_parquet(output / "chunks.parquet")
    retriever = LexicalKnowledgeRetriever(chunks)
    hits = retriever.search("suprimento fundos cartão prestação contas", limit=2)
    assert hits
    assert hits[0].document_id == "norma-teste"
    assert hits[0].retrieval_method == "lexical"
    assert "primary_normative" in format_knowledge_citation(hits[0])


def test_retriever_can_filter_source_class(tmp_path):
    catalog, source_root = _catalog(tmp_path)
    output = tmp_path / "bundle"
    build_knowledge_bundle(catalog, source_root, output, require_all_sources=True)
    chunks = pd.read_parquet(output / "chunks.parquet")
    retriever = LexicalKnowledgeRetriever(chunks)
    hits = retriever.search("auditoria dados inteligência artificial", source_classes={"scientific"})
    assert hits
    assert all(hit.source_class.value == "scientific" for hit in hits)


def test_splitter_is_deterministic(tmp_path):
    source = tmp_path / "texto.md"
    source.write_text("Texto longo. " * 100, encoding="utf-8")
    spec = DocumentSpec(
        document_id="doc-deterministico",
        title="Documento determinístico",
        source_class="project",
        authority_level="project_controlled",
        distribution_policy="project_owned",
        expected_filename="texto.md",
        citation="Projeto. Documento determinístico.",
    )
    sections = load_document(source, spec.document_id)
    first = split_sections(spec, sections, source_sha256="abc", max_chars=400, overlap_chars=40)
    second = split_sections(spec, sections, source_sha256="abc", max_chars=400, overlap_chars=40)
    assert [item.chunk_id for item in first] == [item.chunk_id for item in second]
    assert len(first) > 1


def test_validation_detects_modified_artifact(tmp_path):
    catalog, source_root = _catalog(tmp_path)
    output = tmp_path / "bundle"
    build_knowledge_bundle(catalog, source_root, output, require_all_sources=True)
    (output / "chunks.parquet").write_bytes(b"alterado")
    assert validate_knowledge_bundle(output)["status"] == "FAIL"
