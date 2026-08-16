from __future__ import annotations

import json
from pathlib import Path

from cpgf.knowledge.loader import sha256_file


def validate_retrieval_reference(
    reference_manifest: Path,
    benchmark_path: Path,
    chunks_path: Path,
) -> dict[str, object]:
    """Valida que uma nova avaliação usa exatamente benchmark e corpus de referência."""
    reference_manifest = Path(reference_manifest)
    benchmark_path = Path(benchmark_path)
    chunks_path = Path(chunks_path)
    if not reference_manifest.is_file():
        raise FileNotFoundError(f"Manifesto de referência ausente: {reference_manifest}")
    if not benchmark_path.is_file():
        raise FileNotFoundError(f"Benchmark ausente: {benchmark_path}")
    if not chunks_path.is_file():
        raise FileNotFoundError(f"chunks.parquet ausente: {chunks_path}")

    manifest = json.loads(reference_manifest.read_text(encoding="utf-8"))
    expected_benchmark = str(manifest.get("benchmark_sha256", ""))
    expected_chunks = str(manifest.get("chunks_sha256", ""))
    if not expected_benchmark or not expected_chunks:
        raise ValueError("Manifesto de referência sem hashes de benchmark/corpus")

    actual_benchmark = sha256_file(benchmark_path)
    actual_chunks = sha256_file(chunks_path)
    if actual_benchmark != expected_benchmark:
        raise ValueError("Benchmark divergiu da baseline lexical congelada")
    if actual_chunks != expected_chunks:
        raise ValueError("Corpus/chunks divergiu da baseline lexical congelada")

    return {
        "status": "PASS",
        "reference_manifest": str(reference_manifest.as_posix()),
        "benchmark_sha256": actual_benchmark,
        "chunks_sha256": actual_chunks,
    }
