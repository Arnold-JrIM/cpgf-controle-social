from cpgf.ai import EvidenceLayer, Route, prepare_assistant_state, route_question
from cpgf.benchmark import evaluate_routing, load_benchmark

BENCHMARK = "data/benchmarks/assistant_v1_0_0.csv"


def test_router_supports_all_frozen_benchmark_targets_and_improves_baseline():
    suite = load_benchmark(BENCHMARK)
    summary = evaluate_routing(suite)["summary"]
    assert summary["supported_target_cases"] == 50
    assert summary["accuracy_all"] >= 0.90, summary


def test_knowledge_and_composite_routes_expose_evidence_layers():
    knowledge = route_question("O que é suprimento de fundos?")
    assert knowledge.route is Route.KNOWLEDGE
    assert knowledge.evidence_layers == (EvidenceLayer.KNOWLEDGE,)

    composite = route_question("O fornecedor com mais sinais é necessariamente fraudador?")
    assert composite.route is Route.COMPOSITE
    assert composite.evidence_layers == (
        EvidenceLayer.SERVING,
        EvidenceLayer.METHODOLOGY,
    )


def test_motor_explanation_keeps_methodology_route_with_knowledge_support():
    decision = route_question("Como funciona a trilha T08 baseada na Lei de Benford?")
    assert decision.route is Route.METHODOLOGY
    assert decision.evidence_layers == (
        EvidenceLayer.METHODOLOGY,
        EvidenceLayer.KNOWLEDGE,
    )


def test_state_keeps_route_plan_without_calling_llm_or_tools():
    state = prepare_assistant_state("A T09 prova que o gestor tentou fugir do limite legal?")
    assert state.route is Route.COMPOSITE
    assert state.evidence_layers == (
        EvidenceLayer.METHODOLOGY,
        EvidenceLayer.KNOWLEDGE,
    )
    assert state.llm_called is False
    assert state.tool_request is None


def test_unseen_paraphrases_follow_governed_intents():
    cases = {
        "Explique quem pode receber um suprimento de fundos.": Route.KNOWLEDGE,
        "Mostre quais fornecedores concentram mais sinais.": Route.SUPPLIERS,
        "Quero ver as UGs com mais alertas.": Route.UGS,
        "Mostre o mapa por estado.": Route.TERRITORIAL,
        "Explique a metodologia usada na T03.": Route.METHODOLOGY,
        "Uma divergência de Benford prova fraude?": Route.COMPOSITE,
        "Mostre os sinais das trilhas.": Route.TRAILS,
        "Quero um resumo dos gastos.": Route.OVERVIEW,
    }
    for question, expected in cases.items():
        assert route_question(question).route is expected, question


def test_out_of_domain_question_remains_unsupported():
    assert route_question("Qual é a capital da França?").route is Route.UNSUPPORTED
