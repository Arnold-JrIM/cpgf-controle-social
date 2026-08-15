from __future__ import annotations

from types import SimpleNamespace

from cpgf.benchmark import (
    QuestionFamily,
    evaluate_answer_contract,
    evaluate_retrieval,
    evaluate_routing,
    load_benchmark,
    validate_benchmark_against_catalog,
)


BENCHMARK = "data/benchmarks/assistant_v1_0_0.csv"
CATALOG = "data/knowledge/source_catalog.json"


def test_benchmark_contract_and_distribution():
    suite = load_benchmark(BENCHMARK)
    assert suite.benchmark_version == "1.0.0"
    assert len(suite.cases) == 50

    counts = {family: sum(case.family is family for case in suite.cases) for family in QuestionFamily}
    assert counts[QuestionFamily.CONCEPTUAL_NORMATIVE] == 16
    assert counts[QuestionFamily.SERVING_QUERY] == 8
    assert counts[QuestionFamily.TRAIL_QUERY] == 8
    assert counts[QuestionFamily.MOTOR_RULE] == 9
    assert counts[QuestionFamily.SAFETY_INTERPRETATION] == 9

    covered = {trail for case in suite.cases for trail in case.expected_trails}
    assert covered == {f"T{i:02d}" for i in range(1, 10)}


def test_benchmark_gold_documents_exist_in_knowledge_catalog():
    suite = load_benchmark(BENCHMARK)
    validation = validate_benchmark_against_catalog(suite, CATALOG)
    assert validation["status"] == "PASS"
    assert validation["cases"] == 50
    assert validation["knowledge_cases"] >= 30
    assert validation["serving_cases"] >= 15
    assert validation["freshness_sensitive_cases"] >= 4


def test_router_baseline_is_measurable_without_changing_router():
    suite = load_benchmark(BENCHMARK)
    result = evaluate_routing(suite)
    summary = result["summary"]
    assert summary["cases"] == 50
    assert 0.0 <= summary["accuracy_all"] <= 1.0
    assert summary["supported_target_cases"] < 50
    assert summary["actual_route_counts"]


class FakeRetriever:
    def search(self, query: str, *, limit: int = 5, **filters: object) -> list[object]:
        if "suprimento de fundos" in query.lower():
            return [
                SimpleNamespace(document_id="lei-4320-1964"),
                SimpleNamespace(document_id="decreto-93872-1986"),
            ][:limit]
        return []


def test_document_level_retrieval_metrics_are_deterministic():
    suite = load_benchmark(BENCHMARK)
    result = evaluate_retrieval(suite, FakeRetriever(), k=5)
    summary = result["summary"]
    assert summary["eligible_cases"] > 0
    assert 0.0 <= summary["hit_rate_at_5"] <= 1.0
    assert 0.0 <= summary["mean_document_recall_at_5"] <= 1.0
    assert 0.0 <= summary["mrr"] <= 1.0


def test_answer_contract_checks_concepts_and_forbidden_claims():
    suite = load_benchmark(BENCHMARK)
    case = next(item for item in suite.cases if item.id == "BENCH-046")
    safe = evaluate_answer_contract(
        case,
        "A Lei de Benford é usada como triagem e a divergência não é conclusiva por si só.",
    )
    assert safe["safety_pass"] is True
    assert safe["concept_coverage"] > 0

    unsafe = evaluate_answer_contract(case, "A divergência de Benford prova fraude.")
    assert unsafe["safety_pass"] is False
    assert unsafe["forbidden_claims_found"]
