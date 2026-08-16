from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from cpgf.benchmark import validate_retrieval_reference
from cpgf.knowledge import OpenAIEmbeddingProvider
from cpgf.knowledge.indexing import (
    build_semantic_index,
    persist_semantic_index,
    validate_semantic_index,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Constrói índice semântico local do Knowledge.")
    parser.add_argument("--bundle-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument(
        "--benchmark",
        type=Path,
        default=Path("data/benchmarks/knowledge_retrieval_v1_0_0.csv"),
    )
    parser.add_argument(
        "--reference-baseline-manifest",
        type=Path,
        default=Path("data/manifests/knowledge_lexical_baseline_1_0_0.json"),
    )
    parser.add_argument("--model", default="text-embedding-3-small")
    parser.add_argument("--dimensions", type=int, default=768)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--allow-external-embeddings", action="store_true")
    args = parser.parse_args()

    chunks_path = args.bundle_dir / "chunks.parquet"
    if not chunks_path.is_file():
        raise FileNotFoundError(f"chunks.parquet não encontrado em {args.bundle_dir}")
    if not args.allow_external_embeddings:
        raise ValueError(
            "Construir o índice envia chunks ao provider externo; use --allow-external-embeddings conscientemente"
        )

    reference_validation = validate_retrieval_reference(
        args.reference_baseline_manifest,
        args.benchmark,
        chunks_path,
    )
    output_dir = args.output_dir or args.bundle_dir
    chunks = pd.read_parquet(chunks_path)
    provider = OpenAIEmbeddingProvider(model=args.model, dimensions=args.dimensions)
    index = build_semantic_index(chunks, provider, batch_size=args.batch_size)
    manifest = persist_semantic_index(chunks_path, index, output_dir, provider)
    validation = validate_semantic_index(chunks_path, output_dir)

    print("KNOWLEDGE SEMANTIC INDEX: PASS")
    print(
        json.dumps(
            {
                "reference_validation": reference_validation,
                "manifest": manifest,
                "validation": validation,
                "provider_telemetry": {
                    "external_requests": provider.external_request_count,
                    "embedded_texts": provider.embedded_text_count,
                },
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
