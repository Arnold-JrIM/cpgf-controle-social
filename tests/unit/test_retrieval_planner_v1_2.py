from pathlib import Path

from cpgf.ai import Route, RouteDecision, plan_knowledge_retrieval, route_question
from cpgf.benchmark import (
    evaluate_retrieval_planner,
    load_joint_retrieval_holdout,
    load_retrieval_benchmark,
)
from cpgf.knowledge.models import CorpusScope, TemporalStatus
from cpgf.version import RETRIEVAL_PLANNER_VERSION, ROUTER_VERSION

DEVELOPMENT = Path("data/benchmarks/knowledge_retrieval_v1_0_0.csv")
KNOWN_HOLDOUT = Path("data/benchmarks/retrieval_planner_holdout_v1_0_0.csv")
JOINT_HOLDOUT = Path("data/benchmarks/joint_retrieval_holdout_v2_0_0.csv")


def _assert_retrieval_exact(path: Path) -> None:
    suite = load_retrieval_benchmark(path)
    result = evaluate_retrieval_planner(suite, plan_knowledge_retrieval)
    divergent = [
        row["id"] for row in result["cases_detail"] if not bool(row["joint_exact"])
    ]
    assert result["cases"] == 30
    assert result["scope_exact_match_rate"] == 1.0, divergent
    assert result["temporal_exact_match_rate"] == 1.0, divergent
    assert result["joint_exact_match_rate"] == 1.0, divergent


def _decision(route: Route) -> RouteDecision:
    return RouteDecision(route=route, reason="teste semântico geral do Planner 1.2.0")


def test_planner_1_2_versions() -> None:
    assert ROUTER_VERSION == "1.3.0"
    assert RETRIEVAL_PLANNER_VERSION == "1.2.0"


def test_planner_1_2_preserves_known_60_cases() -> None:
    _assert_retrieval_exact(DEVELOPMENT)
    _assert_retrieval_exact(KNOWN_HOLDOUT)


def test_planner_1_2_recovers_all_known_joint_holdout_filters() -> None:
    suite = load_joint_retrieval_holdout(JOINT_HOLDOUT)
    route_errors: list[str] = []
    filter_errors: list[str] = []

    for case in suite.cases:
        decision = route_question(case.question)
        plan = plan_knowledge_retrieval(case.question, decision=decision)
        if decision.route != case.expected_route:
            route_errors.append(case.id)

        scopes = {item.value for item in plan.scopes}
        expected_scopes = {item.value for item in case.expected_scopes}
        temporal = {item.value for item in plan.temporal_statuses}
        expected_temporal = {item.value for item in case.expected_temporal_statuses}
        if scopes != expected_scopes or temporal != expected_temporal:
            filter_errors.append(case.id)

    assert route_errors == []
    assert filter_errors == []


def test_planner_1_2_uses_general_cross_source_patterns() -> None:
    legal_nature = plan_knowledge_retrieval(
        "O cartão cria uma categoria própria de despesa ou é somente o meio pelo qual ela é paga?",
        decision=_decision(Route.KNOWLEDGE),
    )
    assert legal_nature.scopes == (CorpusScope.CPGF_CORE,)
    assert set(legal_nature.temporal_statuses) == {
        TemporalStatus.CURRENT,
        TemporalStatus.CONTEXTUAL,
    }

    literacy = plan_knowledge_retrieval(
        "Que pesquisa discute a capacidade do cidadão de compreender informações públicas para exercer controle social?",
        decision=_decision(Route.METHODOLOGY),
    )
    assert literacy.scopes == (CorpusScope.METHODOLOGY,)
    assert literacy.temporal_statuses == (TemporalStatus.CONTEXTUAL,)

    external_method = plan_knowledge_retrieval(
        "Que decisão de controle externo e estudo de inteligência de negócios podem apoiar uma fiscalização contínua?",
        decision=_decision(Route.COMPOSITE),
    )
    assert set(external_method.scopes) == {
        CorpusScope.CONTROL_EXTERNAL,
        CorpusScope.METHODOLOGY,
    }
    assert external_method.temporal_statuses == (TemporalStatus.CONTEXTUAL,)

    method_and_guidance = plan_knowledge_retrieval(
        "Que literatura de auditoria e orientação oficial sustentam a validação humana de um sinal analítico?",
        decision=_decision(Route.COMPOSITE),
    )
    assert set(method_and_guidance.scopes) == {
        CorpusScope.CPGF_CORE,
        CorpusScope.METHODOLOGY,
    }
    assert set(method_and_guidance.temporal_statuses) == {
        TemporalStatus.CURRENT,
        TemporalStatus.CONTEXTUAL,
    }
