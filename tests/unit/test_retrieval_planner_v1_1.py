from pathlib import Path

from cpgf.ai import plan_knowledge_retrieval
from cpgf.benchmark import benchmark_sha256, evaluate_retrieval_planner, load_retrieval_benchmark
from cpgf.knowledge.models import CorpusScope, TemporalStatus

DEVELOPMENT = Path("data/benchmarks/knowledge_retrieval_v1_0_0.csv")
KNOWN_HOLDOUT = Path("data/benchmarks/retrieval_planner_holdout_v1_0_0.csv")


def _assert_exact(path: Path) -> None:
    suite = load_retrieval_benchmark(path)
    result = evaluate_retrieval_planner(suite, plan_knowledge_retrieval)
    divergent = [
        row["id"] for row in result["cases_detail"] if not bool(row["joint_exact"])
    ]
    assert result["cases"] == 30
    assert result["scope_exact_match_rate"] == 1.0, divergent
    assert result["temporal_exact_match_rate"] == 1.0, divergent
    assert result["joint_exact_match_rate"] == 1.0, divergent


def test_planner_1_1_frozen_inputs_remain_unchanged() -> None:
    assert benchmark_sha256(DEVELOPMENT) == (
        "6633babe7e17f4c0fefb0523ea477a11257bad87d3c0bc258dea7db1c33c1777"
    )
    assert benchmark_sha256(KNOWN_HOLDOUT) == (
        "ec17f7b2c4c93ae862f0796bfd7a1380b64409fa5270c67b7f00625f1f88a667"
    )


def test_current_planner_preserves_planner_1_1_known_oracles() -> None:
    _assert_exact(DEVELOPMENT)
    _assert_exact(KNOWN_HOLDOUT)


def test_planner_1_1_general_semantic_patterns_remain_supported() -> None:
    nature = plan_knowledge_retrieval(
        "O cartão federal muda a natureza da despesa ou funciona como instrumento de pagamento?"
    )
    assert nature.scopes == (CorpusScope.CPGF_CORE,)
    assert set(nature.temporal_statuses) == {
        TemporalStatus.CURRENT,
        TemporalStatus.CONTEXTUAL,
    }

    social = plan_knowledge_retrieval(
        "Que pesquisas ajudam a relacionar o cartão governamental à fiscalização pela sociedade?"
    )
    assert social.scopes == (CorpusScope.CPGF_CORE, CorpusScope.METHODOLOGY)
    assert social.temporal_statuses == (TemporalStatus.CONTEXTUAL,)

    external = plan_knowledge_retrieval(
        "Que decisão de controle externo pode orientar o monitoramento recorrente do cartão federal?"
    )
    assert external.scopes == (CorpusScope.CONTROL_EXTERNAL,)
    assert external.temporal_statuses == (TemporalStatus.CONTEXTUAL,)
