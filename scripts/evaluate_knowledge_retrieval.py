from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from cpgf.benchmark import (
    benchmark_sha256,
    evaluate_retrieval_benchmark,
    load_retrieval_benchmark,
    validate_retrieval_benchmark_against_catalog,
    validate_retrieval_corpus_coverage,
    validate_retrieval_reference,
)
from cpgf.knowledge import (
    HybridKnowledgeRetriever,
    LexicalKnowledgeRetriever,
    OpenAIEmbeddingProvider,
    SemanticKnowledgeRetriever,
    validate_semantic_index,
)
from cpgf.knowledge.loader import sha256_file
from cpgf.version import KNOWLEDGE_VERSION, RETRIEVAL_BENCHMARK_VERSION


def _parse_methods(value: str) -> tuple[str, ...]:
    methods = tuple(item.strip().lower() for item in value.split(",") if item.strip())
    allowed = {"lexical", "semantic", "hybrid"}
    invalid = sorted(set(methods) - allowed)
    if not methods or invalid:
        raise argparse.ArgumentTypeError(
            "methods deve conter lexical, semantic e/ou hybrid; inválidos=" + str(invalid)
        )
    return methods


def _semantic_retriever(
    chunks: pd.DataFrame,
    chunks_path: Path,
    index_dir: Path,
    *,
    allow_external_embeddings: bool,
) -> tuple[SemanticKnowledgeRetriever, OpenAIEmbeddingProvider]:
    if not allow_external_embeddings:
        raise ValueError(
            "semantic/hybrid requer --allow-external-embeddings; consultas podem ser enviadas ao provider"
        )
    validation = validate_semantic_index(chunks_path, index_dir)
    manifest = json.loads((index_dir / "embeddings_manifest.json").read_text(encoding="utf-8"))
    model = str(manifest["model"])
    dimensions = int(manifest["dimensions"])
    if not model.startswith("text-embedding-"):
        raise ValueError(
            "O avaliador CLI atual só instancia automaticamente índices construídos com OpenAI embeddings"
        )
    provider = OpenAIEmbeddingProvider(model=model, dimensions=dimensions)
    index = pd.read_parquet(index_dir / str(manifest["artifact"]["path"]))
    if int(validation["chunks"]) != len(chunks):
        raise ValueError("Índice semântico e chunks divergem em cardinalidade")
    return SemanticKnowledgeRetriever(chunks, index, provider), provider


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Avalia recuperação documental do Knowledge em corpus local. "
            "Não chama LLM e não executa SQL."
        )
    )
    parser.add_argument(
        "--benchmark",
        type=Path,
        default=Path("data/benchmarks/knowledge_retrieval_v1_0_0.csv"),
    )
    parser.add_argument(
        "--catalog",
        type=Path,
        default=Path("data/knowledge/source_catalog.json"),
    )
    parser.add_argument(
        "--chunks",
        type=Path,
        default=Path("data/knowledge/processed/chunks.parquet"),
    )
    parser.add_argument(
        "--reference-baseline-manifest",
        type=Path,
        default=Path("data/manifests/knowledge_lexical_baseline_1_0_0.json"),
    )
    parser.add_argument("--semantic-index-dir", type=Path)
    parser.add_argument("--methods", type=_parse_methods, default=("lexical",))
    parser.add_argument("--k", type=int, default=5)
    parser.add_argument("--allow-external-embeddings", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    suite = load_retrieval_benchmark(args.benchmark)
    catalog_validation = validate_retrieval_benchmark_against_catalog(suite, args.catalog)
    if not args.chunks.is_file():
        raise FileNotFoundError(
            f"chunks.parquet não encontrado: {args.chunks}. Rode build_knowledge.py localmente primeiro."
        )
    chunks = pd.read_parquet(args.chunks)
    if "document_id" not in chunks.columns:
        raise ValueError("chunks.parquet sem coluna document_id")
    corpus_validation = validate_retrieval_corpus_coverage(
        suite,
        chunks["document_id"].astype(str),
    )
    reference_validation = validate_retrieval_reference(
        args.reference_baseline_manifest,
        args.benchmark,
        args.chunks,
    )

    retrievers: dict[str, object] = {}
    lexical = LexicalKnowledgeRetriever(chunks)
    if "lexical" in args.methods or "hybrid" in args.methods:
        retrievers["lexical"] = lexical

    semantic = None
    provider: OpenAIEmbeddingProvider | None = None
    if "semantic" in args.methods or "hybrid" in args.methods:
        if args.semantic_index_dir is None:
            raise ValueError("semantic/hybrid requer --semantic-index-dir")
        semantic, provider = _semantic_retriever(
            chunks,
            args.chunks,
            args.semantic_index_dir,
            allow_external_embeddings=args.allow_external_embeddings,
        )
        retrievers["semantic"] = semantic
    if "hybrid" in args.methods:
        if semantic is None:
            raise RuntimeError("Retriever semântico não inicializado")
        retrievers["hybrid"] = HybridKnowledgeRetriever(lexical, semantic)

    results: dict[str, object] = {}
    for method in args.methods:
        retriever = retrievers[method]
        results[method] = {
            "governed": evaluate_retrieval_benchmark(
                suite, retriever, k=args.k, governed=True
            ),
            "unfiltered": evaluate_retrieval_benchmark(
                suite, retriever, k=args.k, governed=False
            ),
        }

    payload = {
        "retrieval_benchmark_version": RETRIEVAL_BENCHMARK_VERSION,
        "knowledge_version": KNOWLEDGE_VERSION,
        "benchmark_sha256": benchmark_sha256(args.benchmark),
        "chunks_sha256": sha256_file(args.chunks),
        "reference_validation": reference_validation,
        "k": args.k,
        "methods": list(args.methods),
        "catalog_validation": catalog_validation,
        "corpus_validation": corpus_validation,
        "results": results,
        "provider_telemetry": None
        if provider is None
        else {
            "model": provider.model,
            "dimensions": provider.dimensions,
            "external_requests": provider.external_request_count,
            "embedded_texts": provider.embedded_text_count,
            "query_cache_enabled": provider.cache_enabled,
        },
        "governance": {
            "llm_called": False,
            "sql_executed": False,
            "external_embeddings_allowed": bool(args.allow_external_embeddings),
            "semantic_queries_leave_local_environment_only_when_explicitly_allowed": True,
            "benchmark_and_chunks_locked_to_lexical_baseline": True,
        },
    }
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    print(text)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
