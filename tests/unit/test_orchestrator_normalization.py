from __future__ import annotations

from cpgf.ai.orchestrator_normalization import (
    ORCHESTRATOR_NORMALIZATION_VERSION,
    normalize_orchestrator_payload,
)


def _base_payload() -> dict[str, object]:
    return {
        "reason": "Plano mínimo.",
        "clarification_question": None,
        "data": {
            "selected": False,
            "objective": None,
            "tool": None,
            "parameters": [],
        },
        "knowledge": {
            "selected": False,
            "objective": None,
            "query_hint": None,
            "scopes": [],
            "temporal_statuses": [],
            "source_classes": [],
            "parameters": [],
        },
        "web": {
            "selected": False,
            "objective": None,
            "query_hint": None,
            "freshness_required": False,
            "parameters": [],
        },
    }


def test_normalization_version():
    assert ORCHESTRATOR_NORMALIZATION_VERSION == "1.0.0"


def test_unselected_sources_are_sanitized_before_strict_validation():
    payload = _base_payload()
    payload["knowledge"] = {
        "selected": False,
        "objective": "Texto residual do modelo.",
        "query_hint": "consulta residual",
        "scopes": ["cpgf_core"],
        "temporal_statuses": ["current"],
        "source_classes": ["normative"],
        "parameters": [{"name": "limit", "value": 10}],
    }

    result = normalize_orchestrator_payload("Quais são as 10 UGs mais priorizadas?", payload)

    assert result.payload["knowledge"] == {
        "selected": False,
        "objective": None,
        "query_hint": None,
        "scopes": [],
        "temporal_statuses": [],
        "source_classes": [],
        "parameters": [],
    }
    assert "NORMALIZED_UNSELECTED_KNOWLEDGE" in result.notes


def test_clarification_is_fail_closed_even_if_model_selected_sources():
    payload = _base_payload()
    payload["clarification_question"] = "Qual período você deseja analisar?"
    payload["data"] = {
        "selected": True,
        "objective": "Consultar o painel.",
        "tool": "overview",
        "parameters": [],
    }

    result = normalize_orchestrator_payload("Mostre os gastos.", payload)

    assert result.payload["data"]["selected"] is False
    assert result.payload["data"]["tool"] is None
    assert "CLARIFICATION_FAIL_CLOSED" in result.notes


def test_web_policy_extracts_explicit_freshness_and_ignores_unrelated_numeric_count():
    payload = _base_payload()
    payload["web"] = {
        "selected": True,
        "objective": "Verificar atualização oficial do conjunto de dados.",
        "query_hint": "atualização oficial do CPGF",
        "freshness_required": True,
        "parameters": [
            {"name": "limit", "value": 10},
            {"name": "official_only", "value": False},
            {"name": "max_age_days", "value": None},
        ],
    }

    question = (
        "Quais foram os 10 fornecedores mais recorrentes em 2025 e houve nos últimos 30 dias "
        "mudança oficial na forma de consulta pública dos gastos do CPGF?"
    )
    result = normalize_orchestrator_payload(question, payload)
    web = result.payload["web"]

    assert web["parameters"] == [
        {"name": "limit", "value": 5},
        {"name": "max_age_days", "value": 30},
        {"name": "official_only", "value": True},
    ]
    assert "CANONICALIZED_WEB_PARAMETERS" in result.notes


def test_web_plus_data_drops_knowledge_without_explicit_governed_corpus_intent():
    payload = _base_payload()
    payload["data"] = {
        "selected": True,
        "objective": "Quantificar fornecedores recorrentes.",
        "tool": "top_suppliers",
        "parameters": [],
    }
    payload["knowledge"] = {
        "selected": True,
        "objective": "Interpretar a atualização.",
        "query_hint": "contexto do CPGF",
        "scopes": ["cpgf_core", "methodology"],
        "temporal_statuses": ["current", "historical"],
        "source_classes": ["institutional", "normative"],
        "parameters": [],
    }
    payload["web"] = {
        "selected": True,
        "objective": "Verificar mudança oficial recente.",
        "query_hint": "mudança oficial consulta pública CPGF",
        "freshness_required": True,
        "parameters": [],
    }

    result = normalize_orchestrator_payload(
        "Quais foram os fornecedores mais recorrentes e houve mudança oficial recente na consulta?",
        payload,
    )

    assert result.payload["knowledge"]["selected"] is False
    assert "DROPPED_KNOWLEDGE_WITHOUT_GOVERNED_INTENT" in result.notes


def test_explicit_corpus_intent_keeps_knowledge_and_minimizes_methodology_filters():
    payload = _base_payload()
    payload["knowledge"] = {
        "selected": True,
        "objective": "Recuperar literatura metodológica do corpus sobre Lei de Benford.",
        "query_hint": "literatura metodológica Lei de Benford como triagem",
        "scopes": ["control_external", "cpgf_core", "methodology"],
        "temporal_statuses": ["current", "historical"],
        "source_classes": ["institutional", "normative", "scientific"],
        "parameters": [{"name": "limit", "value": 12}],
    }
    payload["web"] = {
        "selected": True,
        "objective": "Buscar orientação oficial nova.",
        "query_hint": "orientação oficial auditoria de gastos públicos",
        "freshness_required": True,
        "parameters": [],
    }

    result = normalize_orchestrator_payload(
        "Que literatura do corpus sustenta o uso cauteloso da Lei de Benford e que orientação "
        "oficial nova foi publicada nos últimos 90 dias?",
        payload,
    )
    knowledge = result.payload["knowledge"]

    assert knowledge["selected"] is True
    assert knowledge["scopes"] == ["methodology"]
    assert knowledge["temporal_statuses"] == ["contextual"]
    assert knowledge["source_classes"] == ["academic", "scientific"]
    assert knowledge["parameters"] == [{"name": "limit", "value": 5}]


def test_normative_core_filters_are_reduced_to_minimal_governed_set():
    payload = _base_payload()
    payload["knowledge"] = {
        "selected": True,
        "objective": "Recuperar fundamento jurídico do suprimento de fundos.",
        "query_hint": "fundamento jurídico suprimento de fundos adiantamento",
        "scopes": ["control_external", "cpgf_core", "methodology"],
        "temporal_statuses": ["current", "historical"],
        "source_classes": ["institutional", "normative", "scientific"],
        "parameters": [],
    }

    result = normalize_orchestrator_payload(
        "Que fundamento jurídico explica o suprimento de fundos como adiantamento?",
        payload,
    )
    knowledge = result.payload["knowledge"]

    assert knowledge["scopes"] == ["cpgf_core"]
    assert knowledge["temporal_statuses"] == ["current"]
    assert knowledge["source_classes"] == ["normative"]


def test_normalization_is_idempotent():
    payload = _base_payload()
    payload["web"] = {
        "selected": True,
        "objective": "Verificar comunicado oficial recente.",
        "query_hint": "comunicado oficial CPGF",
        "freshness_required": True,
        "parameters": [],
    }
    question = "Houve nos últimos 21 dias comunicado oficial sobre o CPGF?"

    first = normalize_orchestrator_payload(question, payload)
    second = normalize_orchestrator_payload(question, first.payload)

    assert second.payload == first.payload
    assert second.notes == ()
