from pathlib import Path

from cpgf.ai import plan_knowledge_retrieval
from cpgf.benchmark import evaluate_retrieval_planner, load_retrieval_benchmark


BENCHMARK = Path("data/benchmarks/knowledge_retrieval_v1_0_0.csv")


def test_retrieval_planner_diagnostic_uses_frozen_suite_only_post_hoc() -> None:
    suite = load_retrieval_benchmark(BENCHMARK)

    result = evaluate_retrieval_planner(suite, plan_knowledge_retrieval)

    assert result["cases"] == 30
    assert result["governance"] == {
        "planner_input_is_question_only": True,
        "benchmark_oracle_used_only_for_post_hoc_evaluation": True,
    }
    assert len(result["cases_detail"]) == 30
    assert 0.0 <= result["joint_exact_match_rate"] <= 1.0
