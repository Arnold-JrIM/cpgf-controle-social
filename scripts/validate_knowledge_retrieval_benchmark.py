from __future__ import annotations

import argparse
import json
from pathlib import Path

from cpgf.benchmark import (
    benchmark_sha256,
    load_retrieval_benchmark,
    validate_retrieval_benchmark_against_catalog,
)
from cpgf.version import RETRIEVAL_BENCHMARK_VERSION


def main() -> None:
    parser = argparse.ArgumentParser(description="Valida o benchmark documental de recuperação do Knowledge.")
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
    args = parser.parse_args()

    suite = load_retrieval_benchmark(args.benchmark)
    validation = validate_retrieval_benchmark_against_catalog(suite, args.catalog)
    payload = {
        "retrieval_benchmark_version": RETRIEVAL_BENCHMARK_VERSION,
        "benchmark_sha256": benchmark_sha256(args.benchmark),
        **validation,
        "first_real_corpus_measurement_performed": False,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
