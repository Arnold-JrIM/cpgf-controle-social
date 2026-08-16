import hashlib
import unicodedata
from collections import Counter
from pathlib import Path

from cpgf.benchmark import (
    load_retrieval_benchmark,
    validate_retrieval_benchmark_against_catalog,
)

HOLDOUT = Path("data/benchmarks/retrieval_planner_holdout_v1_0_0.csv")
DEVELOPMENT = Path("data/benchmarks/knowledge_retrieval_v1_0_0.csv")
CATALOG = Path("data/knowledge/source_catalog.json")
EXPECTED_SHA256 = "ec17f7b2c4c93ae862f0796bfd7a1380b64409fa5270c67b7f00625f1f88a667"


def _normalize(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text.casefold())
    return " ".join(
        "".join(char for char in decomposed if not unicodedata.combining(char)).split()
    )


def test_retrieval_planner_holdout_is_frozen_and_independent() -> None:
    assert hashlib.sha256(HOLDOUT.read_bytes()).hexdigest() == EXPECTED_SHA256

    holdout = load_retrieval_benchmark(HOLDOUT)
    development = load_retrieval_benchmark(DEVELOPMENT)

    assert len(holdout.cases) == 30
    assert Counter(case.category.value for case in holdout.cases) == {
        "normative": 13,
        "cross_source": 8,
        "methodology": 6,
        "control_external": 3,
    }
    assert {case.id for case in holdout.cases} == {
        f"KRET-{number:03d}" for number in range(101, 131)
    }
    assert not (
        {_normalize(case.question) for case in holdout.cases}
        & {_normalize(case.question) for case in development.cases}
    )
    assert validate_retrieval_benchmark_against_catalog(holdout, CATALOG)["status"] == "PASS"
