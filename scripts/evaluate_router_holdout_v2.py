from __future__ import annotations

import argparse
import hashlib
import json
import unicodedata
from collections import Counter
from pathlib import Path

from cpgf.benchmark import evaluate_routing, load_benchmark
from cpgf.version import BENCHMARK_VERSION, ROUTER_HOLDOUT_V2_VERSION, ROUTER_VERSION

FROZEN_BEFORE_MEASUREMENT_COMMIT = "3a40b0d55e2b9be44bef84a9b5780e3a3f8a0648"
EXPECTED_HOLDOUT_SHA256 = "48be0754b1fb169b7ed882bd8ecdccd72d278d3c2a41dc5bea66f9a8a4ae644e"


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


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Primeira avaliação do Router 1.1.0 no Router Holdout 2.0.0 congelado."
    )
    parser.add_argument(
        "--holdout",
        type=Path,
        default=Path("data/benchmarks/assistant_router_holdout_v2_0_0.csv"),
    )
    parser.add_argument(
        "--development-benchmark",
        type=Path,
        default=Path("data/benchmarks/assistant_v1_0_0.csv"),
    )
    parser.add_argument(
        "--previous-holdout",
        type=Path,
        default=Path("data/benchmarks/assistant_router_holdout_v1_0_0.csv"),
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    holdout = load_benchmark(args.holdout)
    development = load_benchmark(args.development_benchmark)
    previous = load_benchmark(args.previous_holdout)

    holdout_hash = _sha256(args.holdout)
    if holdout_hash != EXPECTED_HOLDOUT_SHA256:
        raise ValueError("Router Holdout 2.0.0 divergiu do hash congelado antes da medição")

    holdout_questions = {_normalize(case.question) for case in holdout.cases}
    reference_questions = {
        _normalize(case.question) for case in (*development.cases, *previous.cases)
    }
    if holdout_questions.intersection(reference_questions):
        raise ValueError("Router Holdout 2.0.0 repete pergunta de conjunto anterior")

    holdout_ids = {case.id for case in holdout.cases}
    reference_ids = {case.id for case in (*development.cases, *previous.cases)}
    if holdout_ids.intersection(reference_ids):
        raise ValueError("Router Holdout 2.0.0 compartilha IDs com conjunto anterior")

    routing = evaluate_routing(holdout)
    payload: dict[str, object] = {
        "holdout_version": ROUTER_HOLDOUT_V2_VERSION,
        "router_version": ROUTER_VERSION,
        "benchmark_schema_version": BENCHMARK_VERSION,
        "frozen_before_measurement_commit": FROZEN_BEFORE_MEASUREMENT_COMMIT,
        "holdout_sha256": holdout_hash,
        "development_benchmark_sha256": _sha256(args.development_benchmark),
        "previous_holdout_sha256": _sha256(args.previous_holdout),
        "question_overlap_exact_with_prior_sets": 0,
        "routing": routing,
        "diagnostics": _routing_diagnostics(routing),
        "interpretation": (
            "O Router Holdout 2.0.0 foi congelado antes da primeira execução do Router 1.1.0 e não foi "
            "usado no ajuste dessa versão. A métrica é uma avaliação interna fora dos conjuntos de ajuste, "
            "não uma estimativa de acurácia de produção ou validação humana externa."
        ),
    }

    text = json.dumps(payload, ensure_ascii=False, indent=2)
    print(text)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
