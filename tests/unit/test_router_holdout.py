from __future__ import annotations

import hashlib
import unicodedata
from collections import Counter
from pathlib import Path

from cpgf.benchmark import QuestionFamily, evaluate_routing, load_benchmark
from cpgf.version import ROUTER_HOLDOUT_VERSION

DEVELOPMENT = Path("data/benchmarks/assistant_v1_0_0.csv")
HOLDOUT = Path("data/benchmarks/assistant_router_holdout_v1_0_0.csv")


def _normalize(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text.casefold())
    return " ".join(
        "".join(char for char in decomposed if not unicodedata.combining(char)).split()
    )


def test_holdout_contract_is_balanced_disjoint_and_covers_all_trails():
    development = load_benchmark(DEVELOPMENT)
    holdout = load_benchmark(HOLDOUT)

    assert ROUTER_HOLDOUT_VERSION == "1.0.0"
    assert len(holdout.cases) == 40

    family_counts = Counter(case.family for case in holdout.cases)
    assert family_counts == Counter({family: 8 for family in QuestionFamily})

    development_ids = {case.id for case in development.cases}
    holdout_ids = {case.id for case in holdout.cases}
    assert development_ids.isdisjoint(holdout_ids)

    development_questions = {_normalize(case.question) for case in development.cases}
    holdout_questions = {_normalize(case.question) for case in holdout.cases}
    assert development_questions.isdisjoint(holdout_questions)

    covered = {trail for case in holdout.cases for trail in case.expected_trails}
    assert covered == {f"T{i:02d}" for i in range(1, 10)}


def test_development_benchmark_remains_frozen():
    digest = hashlib.sha256(DEVELOPMENT.read_bytes()).hexdigest()
    assert digest == "be1a0245f597f9b2456aacdc6485187d6fdb9c52230f0072519d6387148b5820"


def test_router_is_measured_on_holdout_without_historical_accuracy_gate():
    holdout = load_benchmark(HOLDOUT)
    result = evaluate_routing(holdout)
    summary = result["summary"]

    assert summary["cases"] == 40
    assert summary["supported_target_cases"] == 40
    assert 0.0 <= summary["accuracy_all"] <= 1.0
    assert summary["expected_route_counts"]
    assert summary["actual_route_counts"]
