from __future__ import annotations

import hashlib
import json
import unicodedata
from collections import Counter
from pathlib import Path

from cpgf.benchmark import QuestionFamily, load_benchmark
from cpgf.version import ROUTER_HOLDOUT_V2_VERSION

DEVELOPMENT = Path("data/benchmarks/assistant_v1_0_0.csv")
HOLDOUT_V1 = Path("data/benchmarks/assistant_router_holdout_v1_0_0.csv")
HOLDOUT_V2 = Path("data/benchmarks/assistant_router_holdout_v2_0_0.csv")
MANIFEST = Path("data/manifests/assistant_router_holdout_2_0_0.json")


def _normalize(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text.casefold())
    return " ".join(
        "".join(char for char in decomposed if not unicodedata.combining(char)).split()
    )


def test_holdout_v2_is_frozen_balanced_and_disjoint_before_measurement():
    development = load_benchmark(DEVELOPMENT)
    holdout_v1 = load_benchmark(HOLDOUT_V1)
    holdout_v2 = load_benchmark(HOLDOUT_V2)
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))

    assert ROUTER_HOLDOUT_V2_VERSION == "2.0.0"
    assert manifest["holdout_version"] == "2.0.0"
    assert manifest["router_version"] == "1.1.0"
    assert len(holdout_v2.cases) == 40

    digest = hashlib.sha256(HOLDOUT_V2.read_bytes()).hexdigest()
    assert digest == "df48a03af598e86e84bac797f122404db8135c8b77caf19b7024ca52079a298b"
    assert manifest["holdout_sha256"] == digest

    family_counts = Counter(case.family for case in holdout_v2.cases)
    assert family_counts == Counter({family: 8 for family in QuestionFamily})

    v2_ids = {case.id for case in holdout_v2.cases}
    assert v2_ids.isdisjoint({case.id for case in development.cases})
    assert v2_ids.isdisjoint({case.id for case in holdout_v1.cases})

    v2_questions = {_normalize(case.question) for case in holdout_v2.cases}
    assert v2_questions.isdisjoint({_normalize(case.question) for case in development.cases})
    assert v2_questions.isdisjoint({_normalize(case.question) for case in holdout_v1.cases})

    covered = {trail for case in holdout_v2.cases for trail in case.expected_trails}
    assert covered == {f"T{i:02d}" for i in range(1, 10)}
