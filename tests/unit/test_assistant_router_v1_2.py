from pathlib import Path

from cpgf.ai import Route, route_question
from cpgf.benchmark import (
    evaluate_retrieval_flow_attribution,
    evaluate_routing,
    load_benchmark,
    load_retrieval_benchmark,
)

DEVELOPMENT = Path("data/benchmarks/assistant_v1_0_0.csv")
ROUTER_HOLDOUT_V1 = Path("data/benchmarks/assistant_router_holdout_v1_0_0.csv")
ROUTER_HOLDOUT_V2 = Path("data/benchmarks/assistant_router_holdout_v2_0_0.csv")
RETRIEVAL_HOLDOUT = Path("data/benchmarks/retrieval_planner_holdout_v1_0_0.csv")


def test_router_v1_2_preserves_all_known_router_regression_sets() -> None:
    expected_cases = {
        DEVELOPMENT: 50,
        ROUTER_HOLDOUT_V1: 40,
        ROUTER_HOLDOUT_V2: 40,
    }
    for path, cases in expected_cases.items():
        summary = evaluate_routing(load_benchmark(path))["summary"]
        assert summary["cases"] == cases
        assert summary["accuracy_all"] == 1.0, (path, summary)


def test_router_v1_2_removes_router_layer_failures_from_known_retrieval_holdout() -> None:
    suite = load_retrieval_benchmark(RETRIEVAL_HOLDOUT)
    result = evaluate_retrieval_flow_attribution(suite)

    assert result["cases"] == 30
    assert result["joint_filter_failures"] == 9
    assert result["clean_passes"] == 21
    assert result["latent_router_issues_with_exact_filters"] == 0
    assert result["router_contribution_to_joint_failures"] == 0
    assert result["planner_contribution_to_joint_failures"] == 9
    assert result["shared_router_planner_failures"] == 0
    assert result["attribution_counts"] == {"pass": 21, "planner": 9}


def test_router_v1_2_uses_general_semantic_patterns_not_case_ids() -> None:
    cases = {
        "Que referência técnica explica a análise dos primeiros algarismos em auditoria?": (
            Route.METHODOLOGY
        ),
        "Que estudo científico discute painéis como apoio à fiscalização de gastos públicos?": (
            Route.METHODOLOGY
        ),
        "Que normas e orientações oficiais explicam a retirada de numerário pelo cartão governamental?": (
            Route.KNOWLEDGE
        ),
        "Quais referências permitem examinar aquisições repetidas sem presumir irregularidade?": (
            Route.KNOWLEDGE
        ),
        "Uma compra sinalizada pela T01 já autoriza dizer que houve ilícito?": Route.COMPOSITE,
        "Uma anomalia na T08 é suficiente para rotular despesas como fraudulentas?": (
            Route.COMPOSITE
        ),
        "Informe o valor agregado das despesas com CPGF em 2024.": Route.OVERVIEW,
        "Compare DF, SP e RJ pelo valor das transações observáveis em 2025.": (
            Route.TERRITORIAL
        ),
        "Qual é a lógica para classificar saques recorrentes na T07?": Route.METHODOLOGY,
        "É correto comparar um ano ainda parcial com anos completos?": Route.METHODOLOGY,
    }
    for question, expected in cases.items():
        assert route_question(question).route is expected, question
