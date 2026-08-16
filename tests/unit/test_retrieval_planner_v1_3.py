from pathlib import Path

from cpgf.ai import Route, RouteDecision, plan_knowledge_retrieval, route_question
from cpgf.benchmark import (
    evaluate_retrieval_planner,
    load_joint_retrieval_holdout,
    load_retrieval_benchmark,
)
from cpgf.benchmark.joint_retrieval_v3 import load_joint_retrieval_holdout_v3
from cpgf.knowledge.models import CorpusScope, TemporalStatus
from cpgf.version import RETRIEVAL_PLANNER_VERSION, ROUTER_VERSION

DEVELOPMENT = Path("data/benchmarks/knowledge_retrieval_v1_0_0.csv")
KNOWN_HOLDOUT = Path("data/benchmarks/retrieval_planner_holdout_v1_0_0.csv")
JH2 = Path("data/benchmarks/joint_retrieval_holdout_v2_0_0.csv")
JH3 = Path("data/benchmarks/joint_retrieval_holdout_v3_0_0.csv")


def _decision(route: Route) -> RouteDecision:
    return RouteDecision(route=route, reason="teste semântico geral do Planner 1.3.0")


def test_planner_1_3_versions_and_router_isolation() -> None:
    assert RETRIEVAL_PLANNER_VERSION == "1.3.0"
    assert ROUTER_VERSION == "1.4.0"


def test_planner_1_3_preserves_known_retrieval_regressions() -> None:
    for path in (DEVELOPMENT, KNOWN_HOLDOUT):
        result = evaluate_retrieval_planner(
            load_retrieval_benchmark(path),
            plan_knowledge_retrieval,
        )
        assert result["cases"] == 30
        assert result["scope_exact_match_rate"] == 1.0
        assert result["temporal_exact_match_rate"] == 1.0
        assert result["joint_exact_match_rate"] == 1.0


def test_planner_1_3_preserves_joint_holdout_v2_exactness() -> None:
    suite = load_joint_retrieval_holdout(JH2)
    errors: list[str] = []
    for case in suite.cases:
        decision = route_question(case.question)
        plan = plan_knowledge_retrieval(case.question, decision=decision)
        if (
            decision.route != case.expected_route
            or {item.value for item in plan.scopes}
            != {item.value for item in case.expected_scopes}
            or {item.value for item in plan.temporal_statuses}
            != {item.value for item in case.expected_temporal_statuses}
        ):
            errors.append(case.id)
    assert errors == []


def test_planner_1_3_matches_all_known_jh3_filters_with_router_1_4() -> None:
    suite = load_joint_retrieval_holdout_v3(JH3)
    errors: list[tuple[str, list[str], list[str], list[str], list[str]]] = []
    for case in suite.cases:
        decision = route_question(case.question)
        plan = plan_knowledge_retrieval(case.question, decision=decision)
        predicted_scopes = sorted(item.value for item in plan.scopes)
        expected_scopes = sorted(item.value for item in case.expected_scopes)
        predicted_temporal = sorted(item.value for item in plan.temporal_statuses)
        expected_temporal = sorted(item.value for item in case.expected_temporal_statuses)
        if (
            decision.route != case.expected_route
            or predicted_scopes != expected_scopes
            or predicted_temporal != expected_temporal
        ):
            errors.append(
                (
                    case.id,
                    expected_scopes,
                    predicted_scopes,
                    expected_temporal,
                    predicted_temporal,
                )
            )
    assert errors == []


def test_planner_1_3_uses_general_semantic_families_not_case_ids() -> None:
    legal_instrument = plan_knowledge_retrieval(
        "O meio usado para pagar muda a classificação jurídica da despesa ou apenas a operacionaliza?",
        decision=_decision(Route.KNOWLEDGE),
    )
    assert legal_instrument.scopes == (CorpusScope.CPGF_CORE,)
    assert set(legal_instrument.temporal_statuses) == {
        TemporalStatus.CURRENT,
        TemporalStatus.CONTEXTUAL,
    }

    source_bridge = plan_knowledge_retrieval(
        "Que fonte normativa e estudo interpretativo devem ser usados juntos para explicar a natureza do cartão?",
        decision=_decision(Route.COMPOSITE),
    )
    assert source_bridge.scopes == (CorpusScope.CPGF_CORE,)
    assert set(source_bridge.temporal_statuses) == {
        TemporalStatus.CURRENT,
        TemporalStatus.CONTEXTUAL,
    }

    social = plan_knowledge_retrieval(
        "Quais fontes ligam dados do CPGF, capacidade de interpretação e participação social?",
        decision=_decision(Route.COMPOSITE),
    )
    assert set(social.scopes) == {CorpusScope.CPGF_CORE, CorpusScope.METHODOLOGY}
    assert social.temporal_statuses == (TemporalStatus.CONTEXTUAL,)

    method_guidance = plan_knowledge_retrieval(
        "Que literatura metodológica e orientação institucional devem sustentar um painel analítico?",
        decision=_decision(Route.COMPOSITE),
    )
    assert set(method_guidance.scopes) == {CorpusScope.CPGF_CORE, CorpusScope.METHODOLOGY}
    assert set(method_guidance.temporal_statuses) == {
        TemporalStatus.CURRENT,
        TemporalStatus.CONTEXTUAL,
    }

    digital_guidance = plan_knowledge_retrieval(
        "Que base acadêmica sobre padrões digitais e fontes oficiais devem orientar a análise de uma anomalia?",
        decision=_decision(Route.COMPOSITE),
    )
    assert set(digital_guidance.scopes) == {CorpusScope.CPGF_CORE, CorpusScope.METHODOLOGY}
    assert set(digital_guidance.temporal_statuses) == {
        TemporalStatus.CURRENT,
        TemporalStatus.CONTEXTUAL,
    }

    external_normative = plan_knowledge_retrieval(
        "Um pronunciamento do Tribunal de Contas deve ser lido com quais diplomas estruturantes do regime de adiantamento?",
        decision=_decision(Route.COMPOSITE),
    )
    assert set(external_normative.scopes) == {
        CorpusScope.CONTROL_EXTERNAL,
        CorpusScope.CPGF_CORE,
    }
    assert set(external_normative.temporal_statuses) == {
        TemporalStatus.CURRENT,
        TemporalStatus.CONTEXTUAL,
    }

    external_method = plan_knowledge_retrieval(
        "Que fontes de controle externo e estudos metodológicos sustentam usar um sinal automatizado para iniciar verificação?",
        decision=_decision(Route.COMPOSITE),
    )
    assert set(external_method.scopes) == {
        CorpusScope.CONTROL_EXTERNAL,
        CorpusScope.METHODOLOGY,
    }
    assert external_method.temporal_statuses == (TemporalStatus.CONTEXTUAL,)

    social_guidance = plan_knowledge_retrieval(
        "Quais referências unem dados abertos do cartão, educação informacional e orientação pública para acompanhamento cidadão?",
        decision=_decision(Route.COMPOSITE),
    )
    assert set(social_guidance.scopes) == {CorpusScope.CPGF_CORE, CorpusScope.METHODOLOGY}
    assert set(social_guidance.temporal_statuses) == {
        TemporalStatus.CURRENT,
        TemporalStatus.CONTEXTUAL,
    }

    thematic_tcu = plan_knowledge_retrieval(
        "Qual deliberação recente do Tribunal de Contas serve de referência para acompanhamento sistemático das despesas?",
        decision=_decision(Route.KNOWLEDGE),
    )
    assert thematic_tcu.scopes == (CorpusScope.CONTROL_EXTERNAL,)
    assert thematic_tcu.temporal_statuses == (TemporalStatus.CONTEXTUAL,)
