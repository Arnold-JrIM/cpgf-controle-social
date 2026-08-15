from __future__ import annotations

import argparse
import hashlib
import json
import unicodedata
from collections import Counter
from pathlib import Path

from cpgf.benchmark import evaluate_routing, load_benchmark
from cpgf.version import BENCHMARK_VERSION, ROUTER_HOLDOUT_VERSION, ROUTER_VERSION


def _normalize(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text.casefold())
    return " ".join(
        "".join(char for char in decomposed if not unicodedata.combining(char)).split()
    )


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _routing_diagnostics(result: dict[str, object]) -> dict[str, object]:
    rows = list(result["cases"])
    expected_routes = sorted({str(row["expected_route"]) for row in rows})

    per_route: dict[str, object] = {}
    confusion: dict[str, dict[str, int]] = {}
    for expected in expected_routes:
        subset = [row for row in rows if str(row["expected_route"]) == expected]
        exact = sum(bool(row["exact"]) for row in subset)
        per_route[expected] = {
            "cases": len(subset),
            "exact": exact,
            "accuracy": exact / len(subset) if subset else 0.0,
        }
        confusion[expected] = dict(Counter(str(row["actual_route"]) for row in subset))

    errors = [
        {
            "id": row["id"],
            "family": row["family"],
            "expected_route": row["expected_route"],
            "actual_route": row["actual_route"],
        }
        for row in rows
        if not bool(row["exact"])
    ]
    return {
        "per_expected_route": per_route,
        "confusion": confusion,
        "errors": errors,
    }


def _interpretation() -> str:
    if ROUTER_VERSION == "1.0.0":
        return (
            "O holdout é interno ao projeto e não foi usado para ajustar o Router 1.0.0. "
            "A métrica mede generalização para estas formulações, não acurácia de produção."
        )
    return (
        "Os erros observados neste holdout foram disponibilizados após a medição do Router 1.0.0 e podem "
        "ter informado versões posteriores. Para o Router atual, o conjunto deve ser interpretado como "
        "regressão conhecida, não como evidência fora da amostra."
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Avalia o Router atual no holdout interno congelado após o Router 1.0.0."
    )
    parser.add_argument(
        "--holdout",
        type=Path,
        default=Path("data/benchmarks/assistant_router_holdout_v1_0_0.csv"),
    )
    parser.add_argument(
        "--development-benchmark",
        type=Path,
        default=Path("data/benchmarks/assistant_v1_0_0.csv"),
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    holdout = load_benchmark(args.holdout)
    development = load_benchmark(args.development_benchmark)

    holdout_questions = {_normalize(case.question) for case in holdout.cases}
    development_questions = {_normalize(case.question) for case in development.cases}
    overlap = sorted(holdout_questions.intersection(development_questions))
    if overlap:
        raise ValueError("Holdout contém perguntas exatamente repetidas do benchmark de desenvolvimento")

    holdout_ids = {case.id for case in holdout.cases}
    development_ids = {case.id for case in development.cases}
    if holdout_ids.intersection(development_ids):
        raise ValueError("Holdout e benchmark de desenvolvimento compartilham IDs")

    routing = evaluate_routing(holdout)
    payload: dict[str, object] = {
        "holdout_version": ROUTER_HOLDOUT_VERSION,
        "router_version": ROUTER_VERSION,
        "benchmark_schema_version": BENCHMARK_VERSION,
        "holdout_sha256": _sha256(args.holdout),
        "development_benchmark_sha256": _sha256(args.development_benchmark),
        "question_overlap_exact": 0,
        "routing": routing,
        "diagnostics": _routing_diagnostics(routing),
        "interpretation": _interpretation(),
    }

    text = json.dumps(payload, ensure_ascii=False, indent=2)
    print(text)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
