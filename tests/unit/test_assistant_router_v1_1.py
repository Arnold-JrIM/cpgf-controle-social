from cpgf.ai import Route, route_question
from cpgf.benchmark import evaluate_routing, load_benchmark

DEVELOPMENT = "data/benchmarks/assistant_v1_0_0.csv"
KNOWN_HOLDOUT = "data/benchmarks/assistant_router_holdout_v1_0_0.csv"


def test_router_v1_1_preserves_development_benchmark():
    summary = evaluate_routing(load_benchmark(DEVELOPMENT))["summary"]
    assert summary["cases"] == 50
    assert summary["accuracy_all"] == 1.0, summary


def test_router_v1_1_improves_known_holdout_as_regression_set():
    summary = evaluate_routing(load_benchmark(KNOWN_HOLDOUT))["summary"]
    assert summary["cases"] == 40
    assert summary["accuracy_all"] >= 0.90, summary


def test_router_v1_1_handles_generalized_language_patterns():
    cases = {
        "Exiba o montante anual movimentado pelo cartão corporativo federal em 2024.": Route.OVERVIEW,
        "Liste as unidades gestoras com mais sinais no exercício de 2025.": Route.UGS,
        "Compare o gasto por unidade da Federação em 2025.": Route.TERRITORIAL,
        "Qual critério a T04 utiliza para tratar portadores diferentes?": Route.METHODOLOGY,
        "Por que a T07 considera saques sucessivos?": Route.METHODOLOGY,
        "Um sinal T09 basta para afirmar tentativa de burlar o limite?": Route.COMPOSITE,
    }
    for question, expected in cases.items():
        assert route_question(question).route is expected, question
