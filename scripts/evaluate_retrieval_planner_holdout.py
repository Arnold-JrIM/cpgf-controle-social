from __future__ import annotations

import argparse
import hashlib
import json
import unicodedata
from pathlib import Path

from cpgf.ai import plan_knowledge_retrieval
from cpgf.benchmark import (
    evaluate_retrieval_planner,
    load_retrieval_benchmark,
    validate_retrieval_benchmark_against_catalog,
)
from cpgf.version import (
    RETRIEVAL_BENCHMARK_VERSION,
    RETRIEVAL_PLANNER_HOLDOUT_VERSION,
    RETRIEVAL_PLANNER_VERSION,
    ROUTER_VERSION,
)

FROZEN_BEFORE_VALID_MEASUREMENT_COMMIT = "e4b47b5376ff7b9b7f5768ab53f3ba5a6d464265"
EXPECTED_HOLDOUT_SHA256 = "ccbc8b89cb81027b41a380eceaa3ed127663a1d34fc23cf1060e54d1ddcdc480"


def _normalize(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text.casefold())
    return " ".join(
        "".join(char for char in decomposed if not unicodedata.combining(char)).split()
    )


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Avalia o Retrieval Planner 1.0.0 no Holdout 1.0.0 congelado, "
            "sem alterar as regras do planner."
        )
    )
    parser.add_argument(
        "--holdout",
        type=Path,
        default=Path("data/benchmarks/retrieval_planner_holdout_v1_0_0.csv"),
    )
    parser.add_argument(
        "--development-benchmark",
        type=Path,
        default=Path("data/benchmarks/knowledge_retrieval_v1_0_0.csv"),
    )
    parser.add_argument(
        "--catalog",
        type=Path,
        default=Path("data/knowledge/source_catalog.json"),
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    holdout_hash = _sha256(args.holdout)
    if holdout_hash != EXPECTED_HOLDOUT_SHA256:
        raise ValueError("Retrieval Planner Holdout 1.0.0 divergiu do hash congelado")

    holdout = load_retrieval_benchmark(args.holdout)
    development = load_retrieval_benchmark(args.development_benchmark)
    catalog_validation = validate_retrieval_benchmark_against_catalog(holdout, args.catalog)

    holdout_questions = {_normalize(case.question) for case in holdout.cases}
    development_questions = {_normalize(case.question) for case in development.cases}
    overlap = holdout_questions.intersection(development_questions)
    if overlap:
        raise ValueError("Holdout repete pergunta exata do Retrieval Benchmark 1.0.0")

    holdout_ids = {case.id for case in holdout.cases}
    development_ids = {case.id for case in development.cases}
    if holdout_ids.intersection(development_ids):
        raise ValueError("Holdout compartilha IDs com o Retrieval Benchmark 1.0.0")

    planner_result = evaluate_retrieval_planner(holdout, plan_knowledge_retrieval)
    errors = [
        {
            "id": row["id"],
            "route": row["route"],
            "expected_scopes": row["expected_scopes"],
            "predicted_scopes": row["predicted_scopes"],
            "expected_temporal_statuses": row["expected_temporal_statuses"],
            "predicted_temporal_statuses": row["predicted_temporal_statuses"],
            "scope_exact": row["scope_exact"],
            "temporal_exact": row["temporal_exact"],
        }
        for row in planner_result["cases_detail"]
        if not bool(row["joint_exact"])
    ]

    payload: dict[str, object] = {
        "holdout_version": RETRIEVAL_PLANNER_HOLDOUT_VERSION,
        "planner_version": RETRIEVAL_PLANNER_VERSION,
        "router_version": ROUTER_VERSION,
        "benchmark_schema_version": RETRIEVAL_BENCHMARK_VERSION,
        "frozen_before_valid_measurement_commit": FROZEN_BEFORE_VALID_MEASUREMENT_COMMIT,
        "holdout_sha256": holdout_hash,
        "development_benchmark_sha256": _sha256(args.development_benchmark),
        "question_overlap_exact_with_development": 0,
        "catalog_validation": catalog_validation,
        "planner": planner_result,
        "diagnostics": {
            "errors": errors,
            "error_count": len(errors),
        },
        "interpretation": (
            "O Retrieval Planner Holdout 1.0.0 foi congelado antes da primeira execução automatizada "
            "válida do avaliador. O conjunto não foi usado para alterar o Planner 1.0.0. Os resultados "
            "medem generalização interna para novas formulações, não qualidade final de resposta de LLM, "
            "não relevância documental completa e não acurácia de produção."
        ),
    }

    text = json.dumps(payload, ensure_ascii=False, indent=2)
    print(text)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
