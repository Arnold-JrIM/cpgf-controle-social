from __future__ import annotations

import unicodedata
from collections import Counter
from typing import Protocol

from cpgf.ai.router import Route, route_question

from .models import BenchmarkCase, BenchmarkSuite


class Retriever(Protocol):
    def search(self, query: str, *, limit: int = 5, **filters: object) -> list[object]: ...


def _ratio(numerator: int, denominator: int) -> float:
    return 0.0 if denominator == 0 else numerator / denominator


def evaluate_routing(suite: BenchmarkSuite) -> dict[str, object]:
    current_routes = {route.value for route in Route}
    rows: list[dict[str, object]] = []
    for case in suite.cases:
        decision = route_question(case.question)
        expected = case.expected_route.value
        rows.append(
            {
                "id": case.id,
                "family": case.family.value,
                "expected_route": expected,
                "actual_route": decision.route.value,
                "exact": decision.route.value == expected,
                "target_supported_by_current_router": expected in current_routes,
            }
        )

    exact = sum(bool(row["exact"]) for row in rows)
    supported_rows = [row for row in rows if bool(row["target_supported_by_current_router"])]
    exact_supported = sum(bool(row["exact"]) for row in supported_rows)
    return {
        "summary": {
            "cases": len(rows),
            "exact": exact,
            "accuracy_all": _ratio(exact, len(rows)),
            "supported_target_cases": len(supported_rows),
            "exact_supported": exact_supported,
            "accuracy_supported_targets": _ratio(exact_supported, len(supported_rows)),
            "expected_route_counts": dict(Counter(str(row["expected_route"]) for row in rows)),
            "actual_route_counts": dict(Counter(str(row["actual_route"]) for row in rows)),
        },
        "cases": rows,
    }


def evaluate_retrieval(
    suite: BenchmarkSuite,
    retriever: Retriever,
    *,
    k: int = 5,
) -> dict[str, object]:
    if not 1 <= k <= 20:
        raise ValueError("k deve estar entre 1 e 20")
    eligible = [case for case in suite.cases if case.gold_document_ids]
    rows: list[dict[str, object]] = []
    reciprocal_ranks: list[float] = []
    recall_fractions: list[float] = []

    for case in eligible:
        hits = retriever.search(case.question, limit=k)
        retrieved = [str(getattr(hit, "document_id")) for hit in hits]
        gold = set(case.gold_document_ids)
        relevant_positions = [
            index for index, document_id in enumerate(retrieved, start=1) if document_id in gold
        ]
        first_rank = min(relevant_positions) if relevant_positions else None
        unique_relevant = gold.intersection(retrieved)
        recall_fraction = len(unique_relevant) / len(gold)
        reciprocal_rank = 0.0 if first_rank is None else 1.0 / first_rank
        reciprocal_ranks.append(reciprocal_rank)
        recall_fractions.append(recall_fraction)
        rows.append(
            {
                "id": case.id,
                "gold_document_ids": sorted(gold),
                "retrieved_document_ids": retrieved,
                "first_relevant_rank": first_rank,
                f"hit_at_{k}": first_rank is not None,
                f"document_recall_at_{k}": recall_fraction,
                "reciprocal_rank": reciprocal_rank,
            }
        )

    hit_count = sum(bool(row[f"hit_at_{k}"]) for row in rows)
    return {
        "summary": {
            "eligible_cases": len(rows),
            f"hit_rate_at_{k}": _ratio(hit_count, len(rows)),
            f"mean_document_recall_at_{k}": (
                sum(recall_fractions) / len(recall_fractions) if recall_fractions else 0.0
            ),
            "mrr": sum(reciprocal_ranks) / len(reciprocal_ranks) if reciprocal_ranks else 0.0,
        },
        "cases": rows,
    }


def _normalize(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text.casefold())
    return "".join(char for char in normalized if not unicodedata.combining(char))


def evaluate_answer_contract(case: BenchmarkCase, answer: str) -> dict[str, object]:
    normalized = _normalize(answer)
    concepts = [concept for concept in case.expected_concepts if _normalize(concept) in normalized]
    forbidden = [claim for claim in case.forbidden_claims if _normalize(claim) in normalized]
    return {
        "id": case.id,
        "concepts_found": concepts,
        "concept_coverage": _ratio(len(concepts), len(case.expected_concepts)),
        "forbidden_claims_found": forbidden,
        "safety_pass": not forbidden,
    }
