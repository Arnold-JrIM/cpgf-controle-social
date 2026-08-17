from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from cpgf.ai.contracts import ToolName
from cpgf.ai.evidence_contracts import (
    EVIDENCE_CONTRACT_VERSION,
    EvidenceBundle,
    EvidenceItem,
    EvidenceNeed,
    EvidenceParameter,
    EvidencePlan,
    EvidenceSource,
    EvidenceVersion,
)
from cpgf.ai.router import Route
from cpgf.knowledge.models import CorpusScope, SourceClass, TemporalStatus


def _data_need(*, required: bool = True) -> EvidenceNeed:
    return EvidenceNeed(
        need_id="need-data",
        source=EvidenceSource.DATA,
        objective="Recuperar fatos agregados do Serving para a pergunta.",
        required=required,
        tool_hints=(ToolName.TRAIL_PREVALENCE,),
        trail_hints=("t07",),
        parameters=(EvidenceParameter(name="year", value=2025),),
    )


def _knowledge_need(*, required: bool = True) -> EvidenceNeed:
    return EvidenceNeed(
        need_id="need-knowledge",
        source=EvidenceSource.KNOWLEDGE,
        objective="Recuperar fundamento documental governado para contextualizar o resultado.",
        required=required,
        scopes=(CorpusScope.CPGF_CORE, CorpusScope.CONTROL_EXTERNAL),
        temporal_statuses=(TemporalStatus.CURRENT, TemporalStatus.CONTEXTUAL),
        source_classes=(SourceClass.NORMATIVE, SourceClass.CONTROL_EXTERNAL),
        trail_hints=("T07",),
    )


def _web_need(*, required: bool = True) -> EvidenceNeed:
    return EvidenceNeed(
        need_id="need-web",
        source=EvidenceSource.WEB,
        objective="Verificar informação externa atual que não deve ser presumida pelo corpus local.",
        required=required,
        freshness_required=True,
        query_hint="alteração recente CPGF fonte oficial",
    )


def _plan(*needs: EvidenceNeed) -> EvidencePlan:
    return EvidencePlan(
        question="O que os dados mostram e qual fundamento explica esse resultado?",
        needs=needs,
        reason="A pergunta exige combinar fatos observados e evidência documental.",
        legacy_route=Route.COMPOSITE,
    )


def _data_item() -> EvidenceItem:
    return EvidenceItem(
        evidence_id="ev-data-1",
        need_id="need-data",
        source=EvidenceSource.DATA,
        content="A ferramenta retornou 18 unidades UG-ano sinalizadas pela T07 no período.",
        citation="Serving governado — trail_prevalence.",
        source_ref="tool:trail_prevalence",
        tool=ToolName.TRAIL_PREVALENCE,
        retrieval_method="tool",
        parameters=(EvidenceParameter(name="year", value=2025),),
        versions=(
            EvidenceVersion(component="serving", version="1.5.0"),
            EvidenceVersion(component="rules", version="1.2.0"),
        ),
    )


def _knowledge_item() -> EvidenceItem:
    return EvidenceItem(
        evidence_id="ev-knowledge-1",
        need_id="need-knowledge",
        source=EvidenceSource.KNOWLEDGE,
        content="O saque possui tratamento excepcional e deve ser examinado segundo a disciplina aplicável.",
        citation="Decreto e guia oficial recuperados do corpus governado.",
        source_ref="chunk:decreto-6370-2008:12",
        document_id="decreto-6370-2008",
        chunk_id="decreto-6370-2008:12",
        page=2,
        scope=CorpusScope.CPGF_CORE,
        temporal_status=TemporalStatus.CURRENT,
        source_class=SourceClass.NORMATIVE,
        retrieval_score=0.91,
        retrieval_method="hybrid",
        versions=(EvidenceVersion(component="knowledge", version="1.2.0"),),
    )


def _web_item() -> EvidenceItem:
    return EvidenceItem(
        evidence_id="ev-web-1",
        need_id="need-web",
        source=EvidenceSource.WEB,
        content="A fonte oficial consultada informa a atualização corrente.",
        citation="Fonte oficial consultada na web.",
        source_ref="https://www.gov.br/exemplo",
        source_url="https://www.gov.br/exemplo",
        observed_at=datetime(2026, 8, 17, 11, 0, tzinfo=timezone.utc),
        retrieval_method="web",
        source_class=SourceClass.WEB,
    )


def test_plan_is_multi_label_and_preserves_legacy_route_only_as_metadata():
    plan = _plan(_data_need(), _knowledge_need(), _web_need(required=False))

    assert EVIDENCE_CONTRACT_VERSION == "1.0.0"
    assert plan.requested_sources == (
        EvidenceSource.DATA,
        EvidenceSource.KNOWLEDGE,
        EvidenceSource.WEB,
    )
    assert plan.required_sources == (EvidenceSource.DATA, EvidenceSource.KNOWLEDGE)
    assert plan.need_for(EvidenceSource.KNOWLEDGE).need_id == "need-knowledge"
    assert plan.legacy_route is Route.COMPOSITE


def test_plan_allows_zero_needs_for_unsupported_or_non_evidential_turns():
    plan = EvidencePlan(
        question="Olá, o que este assistente faz?",
        needs=(),
        reason="Turno de orientação sem necessidade de recuperar evidência.",
    )

    assert plan.requested_sources == ()
    assert plan.required_sources == ()


def test_plan_rejects_duplicate_sources_and_duplicate_need_ids():
    with pytest.raises(ValidationError, match="uma necessidade agregada por fonte"):
        _plan(
            _data_need(),
            EvidenceNeed(
                need_id="need-data-2",
                source=EvidenceSource.DATA,
                objective="Executar uma segunda necessidade redundante de dados.",
            ),
        )

    with pytest.raises(ValidationError, match="need_id deve ser único"):
        _plan(_data_need(), _knowledge_need().model_copy(update={"need_id": "need-data"}))


def test_need_rejects_source_contract_leakage():
    with pytest.raises(ValidationError, match="não pertencem a DATA"):
        EvidenceNeed(
            need_id="need-data",
            source=EvidenceSource.DATA,
            objective="Consultar dados do Serving.",
            scopes=(CorpusScope.CPGF_CORE,),
        )

    with pytest.raises(ValidationError, match="somente para evidência DATA"):
        EvidenceNeed(
            need_id="need-knowledge",
            source=EvidenceSource.KNOWLEDGE,
            objective="Consultar corpus governado.",
            tool_hints=(ToolName.OVERVIEW,),
        )


def test_trails_are_normalized_and_validated():
    need = EvidenceNeed(
        need_id="need-data",
        source=EvidenceSource.DATA,
        objective="Consultar uma trilha específica.",
        trail_hints=("t07", "T07"),
    )
    assert need.trail_hints == ("T07",)

    with pytest.raises(ValidationError, match="Trilhas inválidas"):
        EvidenceNeed(
            need_id="need-data",
            source=EvidenceSource.DATA,
            objective="Consultar uma trilha inexistente.",
            trail_hints=("T99",),
        )


def test_evidence_item_enforces_source_specific_provenance():
    assert _data_item().tool is ToolName.TRAIL_PREVALENCE
    assert _knowledge_item().document_id == "decreto-6370-2008"
    assert _web_item().source_url == "https://www.gov.br/exemplo"

    with pytest.raises(ValidationError, match="DATA exige tool"):
        EvidenceItem(
            evidence_id="ev-data-invalid",
            need_id="need-data",
            source=EvidenceSource.DATA,
            content="Resultado sem ferramenta identificada.",
            citation="Sem proveniência suficiente.",
            source_ref="unknown",
        )

    with pytest.raises(ValidationError, match="KNOWLEDGE exige document_id"):
        EvidenceItem(
            evidence_id="ev-knowledge-invalid",
            need_id="need-knowledge",
            source=EvidenceSource.KNOWLEDGE,
            content="Trecho sem documento de origem.",
            citation="Sem document_id.",
            source_ref="unknown",
        )

    with pytest.raises(ValidationError, match="WEB exige source_url e observed_at"):
        EvidenceItem(
            evidence_id="ev-web-invalid",
            need_id="need-web",
            source=EvidenceSource.WEB,
            content="Resultado externo sem momento de observação.",
            citation="Fonte externa incompleta.",
            source_ref="https://www.gov.br/exemplo",
            source_url="https://www.gov.br/exemplo",
        )


def test_bundle_accepts_partial_fan_in_and_reports_missing_required_needs():
    plan = _plan(_data_need(), _knowledge_need(), _web_need(required=False))
    bundle = EvidenceBundle(plan=plan, items=(_data_item(),))

    assert bundle.satisfied_need_ids == ("need-data",)
    assert bundle.missing_required_need_ids == ("need-knowledge",)
    assert bundle.is_complete is False
    assert bundle.items_for(EvidenceSource.DATA) == (_data_item(),)

    complete = EvidenceBundle(plan=plan, items=(_data_item(), _knowledge_item()))
    assert complete.is_complete is True
    assert complete.missing_required_need_ids == ()


def test_bundle_rejects_unplanned_or_source_mismatched_evidence():
    plan = _plan(_data_need(), _knowledge_need())

    unplanned = _web_item()
    with pytest.raises(ValidationError, match="need_id não planejado"):
        EvidenceBundle(plan=plan, items=(unplanned,))

    mismatched = _knowledge_item().model_copy(
        update={"need_id": "need-data", "evidence_id": "ev-mismatch"}
    )
    with pytest.raises(ValidationError, match="fonte knowledge incompatível"):
        EvidenceBundle(plan=plan, items=(mismatched,))


def test_contracts_are_strict_frozen_and_json_serializable():
    plan = _plan(_data_need(), _knowledge_need())
    bundle = EvidenceBundle(plan=plan, items=(_data_item(), _knowledge_item()))

    with pytest.raises(ValidationError):
        plan.question = "mutação não autorizada"  # type: ignore[misc]

    with pytest.raises(ValidationError):
        EvidencePlan.model_validate(
            {
                "question": "Pergunta válida para o contrato.",
                "reason": "Razão válida.",
                "needs": [],
                "campo_extra": "não permitido",
            }
        )

    payload = bundle.model_dump(mode="json")
    assert payload["contract_version"] == "1.0.0"
    assert payload["plan"]["needs"][0]["source"] == "data"
    assert payload["items"][0]["tool"] == "trail_prevalence"
