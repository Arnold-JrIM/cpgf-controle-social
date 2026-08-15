from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from cpgf.benchmark import (
    evaluate_retrieval,
    evaluate_routing,
    load_benchmark,
    validate_benchmark_against_catalog,
)
from cpgf.knowledge import (
    HybridKnowledgeRetriever,
    LexicalKnowledgeRetriever,
    OpenAIEmbeddingProvider,
    SemanticKnowledgeRetriever,
)
from cpgf.knowledge.indexing import validate_semantic_index


def _retriever(
    method: str,
    bundle_dir: Path,
    embeddings_dir: Path | None,
    allow_external_embeddings: bool,
) -> object:
    chunks_path = bundle_dir / "chunks.parquet"
    if not chunks_path.is_file():
        raise FileNotFoundError(f"chunks.parquet não encontrado em {bundle_dir}")
    chunks = pd.read_parquet(chunks_path)
    lexical = LexicalKnowledgeRetriever(chunks)
    if method == "lexical":
        return lexical

    if not allow_external_embeddings:
        raise RuntimeError(
            "Recuperação semantic/hybrid exige --allow-external-embeddings, pois a consulta "
            "será enviada explicitamente ao provedor de embeddings."
        )
    index_dir = embeddings_dir or bundle_dir
    validation = validate_semantic_index(chunks_path, index_dir)
    manifest = json.loads((index_dir / "embeddings_manifest.json").read_text(encoding="utf-8"))
    embeddings = pd.read_parquet(index_dir / "embeddings.parquet")
    provider = OpenAIEmbeddingProvider(
        model=str(manifest["model"]),
        dimensions=int(validation["dimensions"]),
    )
    semantic = SemanticKnowledgeRetriever(chunks, embeddings, provider)
    if method == "semantic":
        return semantic
    return HybridKnowledgeRetriever(lexical, semantic)


def main() -> None:
    parser = argparse.ArgumentParser(description="Avalia benchmark governado do Assistente CPGF.")
    parser.add_argument(
        "--benchmark",
        type=Path,
        default=Path("data/benchmarks/assistant_v1_0_0.csv"),
    )
    parser.add_argument(
        "--catalog",
        type=Path,
        default=Path("data/knowledge/source_catalog.json"),
    )
    parser.add_argument("--bundle-dir", type=Path)
    parser.add_argument(
        "--retrieval-method",
        choices=("lexical", "semantic", "hybrid"),
        default="lexical",
    )
    parser.add_argument("--embeddings-dir", type=Path)
    parser.add_argument("--allow-external-embeddings", action="store_true")
    parser.add_argument("--k", type=int, default=5)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    suite = load_benchmark(args.benchmark)
    catalog_validation = validate_benchmark_against_catalog(suite, args.catalog)
    result: dict[str, object] = {
        "benchmark_version": suite.benchmark_version,
        "catalog_validation": catalog_validation,
        "routing": evaluate_routing(suite),
    }

    if args.bundle_dir:
        retriever = _retriever(
            args.retrieval_method,
            args.bundle_dir,
            args.embeddings_dir,
            args.allow_external_embeddings,
        )
        result["retrieval"] = {
            "method": args.retrieval_method,
            **evaluate_retrieval(suite, retriever, k=args.k),
        }

    text = json.dumps(result, ensure_ascii=False, indent=2)
    print(text)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
