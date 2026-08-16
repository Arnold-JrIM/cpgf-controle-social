import json
from pathlib import Path

from cpgf.ai import Route, route_question
from cpgf.benchmark import evaluate_routing, load_benchmark, load_joint_retrieval_holdout

DEVELOPMENT = Path("data/benchmarks/assistant_v1_0_0.csv")
ROUTER_HOLDOUT_V1 = Path("data/benchmarks/assistant_router_holdout_v1_0_0.csv")
ROUTER_HOLDOUT_V2 = Path("data/benchmarks/assistant_router_holdout_v2_0_0.csv")
JOINT_HOLDOUT_V2 = Path("data/benchmarks/joint_retrieval_holdout_v2_0_0.csv")
ROUTER_V1_3_MANIFEST = Path("data/manifests/assistant_router_1_3_0.json")


def test_router_v1_3_historical_version_remains_frozen() -> None:
    manifest = json.loads(ROUTER_V1_3_MANIFEST.read_text(encoding="utf-8"))
    assert manifest["router_version"] == "1.3.0"
    assert manifest["router_source_git_blob_sha"] == (
        "7c82b42f4409110371dcb86e15672a328a0d54bd"
    )


def test_current_router_preserves_router_v1_3_known_regression_sets() -> None:
    expected_cases = {
        DEVELOPMENT: 50,
        ROUTER_HOLDOUT_V1: 40,
        ROUTER_HOLDOUT_V2: 40,
    }
    for path, cases in expected_cases.items():
        summary = evaluate_routing(load_benchmark(path))["summary"]
        assert summary["cases"] == cases
        assert summary["accuracy_all"] == 1.0, (path, summary)


def test_current_router_matches_all_known_joint_holdout_v2_routes() -> None:
    suite = load_joint_retrieval_holdout(JOINT_HOLDOUT_V2)
    errors = [
        (case.id, case.expected_route.value, route_question(case.question).route.value)
        for case in suite.cases
        if route_question(case.question).route != case.expected_route
    ]
    assert errors == []


def test_router_v1_3_semantic_families_remain_supported() -> None:
    cases = {
        "Qual trabalho acadêmico discute business intelligence para selecionar gastos que merecem fiscalização?": Route.METHODOLOGY,
        "Existe pesquisa recente sobre inteligência artificial como apoio à auditoria de recursos públicos?": Route.METHODOLOGY,
        "Um resultado isolado de uma distribuição numérica fora do padrão esperado basta para diagnosticar fraude?": Route.METHODOLOGY,
        "Que estudo discute a capacidade do cidadão de compreender o Portal da Transparência para exercer controle social?": Route.METHODOLOGY,
        "Existe artigo acadêmico sobre contratação direta com cartão e qual norma vigente deve ser lida junto?": Route.COMPOSITE,
        "Que decisão de controle externo e estudo científico podem ser combinados para discutir fiscalização contínua?": Route.COMPOSITE,
        "Como articular um precedente do TCU com as normas gerais de suprimento de fundos?": Route.COMPOSITE,
        "Quais referências relacionam transparência dos gastos do cartão, competência informacional e fiscalização pela sociedade?": Route.COMPOSITE,
        "Se um agente recebe recursos por suprimento, em quais fontes oficiais estão as regras de responsabilidade?": Route.KNOWLEDGE,
        "Usar o cartão do governo cria uma nova categoria de despesa?": Route.KNOWLEDGE,
        "Como reconstruir a sequência de portarias que regulamentou o cartão?": Route.KNOWLEDGE,
        "Preciso consultar um Acórdão do TCU; qual documento corresponde à decisão?": Route.KNOWLEDGE,
    }
    for question, expected in cases.items():
        assert route_question(question).route is expected, question
