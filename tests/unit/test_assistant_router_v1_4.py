from pathlib import Path

from cpgf.ai import Route, route_question
from cpgf.benchmark import evaluate_routing, load_benchmark, load_joint_retrieval_holdout
from cpgf.benchmark.joint_retrieval_v3 import load_joint_retrieval_holdout_v3
from cpgf.version import ROUTER_VERSION

DEVELOPMENT = Path("data/benchmarks/assistant_v1_0_0.csv")
ROUTER_HOLDOUT_V1 = Path("data/benchmarks/assistant_router_holdout_v1_0_0.csv")
ROUTER_HOLDOUT_V2 = Path("data/benchmarks/assistant_router_holdout_v2_0_0.csv")
JH2 = Path("data/benchmarks/joint_retrieval_holdout_v2_0_0.csv")
JH3 = Path("data/benchmarks/joint_retrieval_holdout_v3_0_0.csv")


def test_router_v1_4_version_is_current() -> None:
    assert ROUTER_VERSION == "1.4.0"


def test_router_v1_4_preserves_all_prior_router_regressions() -> None:
    for path, cases in (
        (DEVELOPMENT, 50),
        (ROUTER_HOLDOUT_V1, 40),
        (ROUTER_HOLDOUT_V2, 40),
    ):
        summary = evaluate_routing(load_benchmark(path))["summary"]
        assert summary["cases"] == cases
        assert summary["accuracy_all"] == 1.0, (path, summary)

    jh2 = load_joint_retrieval_holdout(JH2)
    jh2_errors = [
        case.id
        for case in jh2.cases
        if route_question(case.question).route != case.expected_route
    ]
    assert jh2_errors == []


def test_router_v1_4_matches_all_jh3_routes_as_known_regression() -> None:
    suite = load_joint_retrieval_holdout_v3(JH3)
    errors = [
        (case.id, case.expected_route.value, route_question(case.question).route.value)
        for case in suite.cases
        if route_question(case.question).route != case.expected_route
    ]
    assert errors == []


def test_router_v1_4_semantic_expansion_uses_general_families() -> None:
    cases = {
        "Ao receber suprimento, quais deveres de aplicação e comprovação recaem sobre o responsável?": Route.KNOWLEDGE,
        "Qual combinação normativa rege os limites do suprimento vinculados à contratação direta?": Route.KNOWLEDGE,
        "Para reconstruir a sequência regulatória do cartão, que atos ministeriais devem ser consultados?": Route.KNOWLEDGE,
        "Uma compra direta paga via suprimento deve ser confrontada com qual lei de licitações?": Route.KNOWLEDGE,
        "Há pesquisa empírica que tenha aplicado análise digital a despesas governamentais?": Route.METHODOLOGY,
        "Qual literatura explica técnicas forenses baseadas em dígitos e seus limites interpretativos?": Route.METHODOLOGY,
        "Qual estudo mostra como inteligência de negócios ajuda a priorizar gastos públicos para fiscalização?": Route.METHODOLOGY,
        "Que normas e estudos sobre compras repetidas ajudam a contextualizar o padrão antes de qualquer conclusão jurídica?": Route.COMPOSITE,
        "Que base acadêmica e fontes oficiais devem ser combinadas para analisar uma anomalia sem chamá-la de fraude?": Route.COMPOSITE,
        "Um pronunciamento do TCU e diplomas estruturantes do regime de adiantamento devem ser lidos juntos. Que fontes usar?": Route.COMPOSITE,
        "Quais fontes ligam dados do CPGF, capacidade de interpretação e participação social?": Route.COMPOSITE,
        "Quais referências unem dados abertos do cartão, educação informacional e acompanhamento cidadão?": Route.COMPOSITE,
    }
    for question, expected in cases.items():
        assert route_question(question).route is expected, question


def test_router_v1_4_direct_named_control_external_lookup_stays_knowledge() -> None:
    question = (
        "Em uma consulta documental sobre o Acórdão 2.000/2026, qual fonte oficial "
        "do universo de controle externo deve ser selecionada?"
    )
    assert route_question(question).route is Route.KNOWLEDGE


def test_router_v1_4_does_not_steal_quantitative_requests() -> None:
    assert route_question("Mostre a quantidade de alertas T08 por ano para Benford.").route is Route.TRAILS
    assert route_question("Compare o gasto total de SP e RJ.").route is Route.TERRITORIAL
