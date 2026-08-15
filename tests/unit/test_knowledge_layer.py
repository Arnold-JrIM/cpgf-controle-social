from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from cpgf.knowledge import (
    LexicalKnowledgeRetriever,
    build_knowledge_bundle,
    load_source_catalog,
    validate_knowledge_bundle,
)
from cpgf.knowledge.models import DocumentSpec


def _catalog(tmp_path: Path) -> tuple[Path, Path]:
    sources = tmp_path / "sources"
    (sources / "normas").mkdir(parents=True)
    (sources / "historico").mkdir()
    (sources / "normas" / "norma.md").write_text("Suprimento de fundos e prestação de contas.", encoding="utf-8")
    (sources / "historico" / "lei.txt").write_text("Regra histórica revogada.", encoding="utf-8")
    payload = {"documents": [
        {"document_id":"norma-teste","title":"Norma de teste","source_class":"normative","authority_level":"primary_normative","distribution_policy":"public_official","expected_path":"normas/norma.md","citation":"ÓRGÃO. Norma de teste.","supports_trails":["T03"]},
        {"document_id":"historico-teste","title":"Histórico de teste","source_class":"normative","authority_level":"primary_normative","distribution_policy":"public_official","expected_path":"historico/lei.txt","citation":"ÓRGÃO. Histórico de teste.","scope":"historical","temporal_status":"historical","retrieval_default":False}
    ]}
    catalog = tmp_path / "catalog.json"
    catalog.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return catalog, sources


def test_real_catalog_governance_counts():
    catalog = load_source_catalog(Path("data/knowledge/source_catalog.json"))
    assert len(catalog) == 45
    assert sum(item.retrieval_default for item in catalog) == 35
    assert sum(item.scope.value == "control_external" for item in catalog) == 11
    assert sum(item.scope.value == "methodology" for item in catalog) == 6
    assert sum(item.scope.value == "historical" for item in catalog) == 1
    assert sum(item.scope.value == "institutional_mb" for item in catalog) == 4
    assert sum(item.scope.value == "discovery" for item in catalog) == 3
    assert any(item.document_id == "decreto-12807-2025" and item.source_relative_path is None for item in catalog)
    assert any(item.document_id == "siafi-macrofuncao-021121-2026" and not item.ingest_content for item in catalog)


def test_expected_path_accepts_nested_and_rejects_traversal():
    spec = DocumentSpec(
        document_id="doc-teste",
        title="Documento teste",
        source_class="scientific",
        authority_level="scientific_peer_reviewed",
        distribution_policy="metadata_only",
        expected_path="artigos/documento.pdf",
        citation="Teste.",
    )
    assert spec.source_relative_path == "artigos/documento.pdf"
    with pytest.raises(ValueError):
        DocumentSpec(
            document_id="doc-invalido",
            title="Documento inválido",
            source_class="scientific",
            authority_level="scientific_peer_reviewed",
            distribution_policy="metadata_only",
            expected_path="../segredo.pdf",
            citation="Teste.",
        )


def test_build_validate_and_default_retrieval(tmp_path: Path):
    catalog, sources = _catalog(tmp_path)
    output = tmp_path / "bundle"
    manifest = build_knowledge_bundle(catalog, sources, output, require_all_sources=True, require_text_sources=True)
    assert manifest["knowledge_version"] == "1.1.0"
    assert manifest["documents"] == 2
    assert manifest["documents_available"] == 2
    assert manifest["documents_retrieval_default"] == 1
    assert validate_knowledge_bundle(output)["status"] == "PASS"
    chunks = pd.read_parquet(output / "chunks.parquet")
    retriever = LexicalKnowledgeRetriever(chunks)
    assert retriever.search("suprimento prestação")[0].document_id == "norma-teste"
    assert retriever.search("histórica revogada") == []
    assert retriever.search("histórica revogada", include_non_default=True)[0].document_id == "historico-teste"


def test_source_contract_mismatch_fails(tmp_path: Path):
    sources = tmp_path / "sources"
    sources.mkdir()
    source = sources / "norma.txt"
    source.write_text("texto", encoding="utf-8")
    catalog = tmp_path / "catalog.json"
    catalog.write_text(json.dumps({"documents":[{
        "document_id":"contrato-teste","title":"Contrato teste","source_class":"normative","authority_level":"primary_normative","distribution_policy":"public_official","expected_filename":"norma.txt","expected_sha256":"0" * 64,"citation":"Teste."
    }]}), encoding="utf-8")
    with pytest.raises(ValueError, match="Fonte divergiu do contrato"):
        build_knowledge_bundle(catalog, sources, tmp_path / "bundle")


def test_default_no_text_can_be_strictly_rejected(tmp_path: Path):
    sources = tmp_path / "sources"
    sources.mkdir()
    (sources / "vazio.txt").write_text("", encoding="utf-8")
    catalog = tmp_path / "catalog.json"
    catalog.write_text(json.dumps({"documents":[{
        "document_id":"vazio-teste","title":"Vazio teste","source_class":"institutional","authority_level":"official_institutional","distribution_policy":"public_official","expected_filename":"vazio.txt","citation":"Teste."
    }]}), encoding="utf-8")
    with pytest.raises(ValueError, match="sem texto extraível"):
        build_knowledge_bundle(catalog, sources, tmp_path / "bundle", require_text_sources=True)


def test_duplicate_source_path_is_rejected(tmp_path: Path):
    catalog = tmp_path / "catalog.json"
    catalog.write_text(json.dumps({"documents":[
        {"document_id":"doc-um","title":"Documento um","source_class":"project","authority_level":"project_controlled","distribution_policy":"project_owned","expected_filename":"mesmo.txt","citation":"Um."},
        {"document_id":"doc-dois","title":"Documento dois","source_class":"project","authority_level":"project_controlled","distribution_policy":"project_owned","expected_filename":"mesmo.txt","citation":"Dois."}
    ]}), encoding="utf-8")
    with pytest.raises(ValueError, match="caminho de fonte duplicado"):
        load_source_catalog(catalog)
