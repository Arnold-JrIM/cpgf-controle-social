from __future__ import annotations

import json
from pathlib import Path

import pytest

from cpgf.benchmark import validate_retrieval_reference
from cpgf.knowledge.loader import sha256_file


def _reference(tmp_path: Path) -> tuple[Path, Path, Path]:
    benchmark = tmp_path / "benchmark.csv"
    chunks = tmp_path / "chunks.parquet"
    benchmark.write_text("case_id,question\nKRET-X,Teste\n", encoding="utf-8")
    chunks.write_bytes(b"parquet-placeholder")
    manifest = tmp_path / "baseline.json"
    manifest.write_text(
        json.dumps(
            {
                "benchmark_sha256": sha256_file(benchmark),
                "chunks_sha256": sha256_file(chunks),
            }
        ),
        encoding="utf-8",
    )
    return manifest, benchmark, chunks


def test_reference_validation_passes_for_same_artifacts(tmp_path: Path):
    manifest, benchmark, chunks = _reference(tmp_path)
    result = validate_retrieval_reference(manifest, benchmark, chunks)
    assert result["status"] == "PASS"
    assert result["benchmark_sha256"] == sha256_file(benchmark)
    assert result["chunks_sha256"] == sha256_file(chunks)


def test_reference_validation_rejects_changed_benchmark(tmp_path: Path):
    manifest, benchmark, chunks = _reference(tmp_path)
    benchmark.write_text("alterado", encoding="utf-8")
    with pytest.raises(ValueError, match="Benchmark divergiu"):
        validate_retrieval_reference(manifest, benchmark, chunks)


def test_reference_validation_rejects_changed_chunks(tmp_path: Path):
    manifest, benchmark, chunks = _reference(tmp_path)
    chunks.write_bytes(b"outro-corpus")
    with pytest.raises(ValueError, match="Corpus/chunks divergiu"):
        validate_retrieval_reference(manifest, benchmark, chunks)
