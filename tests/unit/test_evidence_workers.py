from __future__ import annotations

import json

from cpgf.ai.contracts import ToolName, ToolProvenance, ToolResult
from cpgf.ai.evidence_contracts import (
    EvidenceNeed,
    EvidenceParameter,
    EvidencePlan,
    EvidenceSource,
)
from cpgf.ai.evidence_workers import (
    EVIDENCE_WORKER_VERSION,
    disabled_web_need,
    execute_data_need,
    retrieve_knowledge_need,
)
from cpgf.ai.orchestration_graph import run_evidence_orchestration
from cpgf.knowledge.models import (
    AuthorityLevel,
    CorpusScope,
    SearchHit,
    SourceClass,
    TemporalStatus,
)


def _plan(*needs: EvidenceNeed) -> EvidencePlan:
    return EvidencePlan(
        question="Quais evidências sustentam a análise do CPGF em 2025?",
        reason="Teste dos executores governados.",
        needs=needs,
    )


def test_worker_version():
    assert EVIDENCE_WORKER_VERSION == "1.0.0"


def test_data_worker_executes_only_registered_read_only_tool(monkeypatch):
    need = EvidenceNeed(
        need_id="need-data",
        source=EvidenceSource.DATA,
        objective="Consultar visão geral materializada.",
        tool_hints=(ToolName.OVERVIEW,),
        parameters=(
            EvidenceParameter(name="year_start", value=2025),
            EvidenceParameter(name="year_end", value=2025),
        ),
    )
    plan = _plan(need)
    calls: list[object] = []

    def fake_execute_tool(context, request):
        calls.append((context, request))
        return ToolResult(
            tool=ToolName.OVERVIEW,
            records=[{"ANO": 2025, "UGS": 2}],
            summary={"ugs": 2, "operations": 15},
            provenance=ToolProvenance(
                serving_version="1.5.0",
                rules_version="1.2.0",
                motor_version="1.3.2",
                geo_version="1.1.0",
                read_only=True,
                source="serving_views",
            ),
        )

    monkeypatch.setattr("cpgf.ai.evidence_workers.execute_tool", fake_execute_tool)
    context = object()
    outcome = execute_data_need(plan=plan, need=need, context=context)  # type: ignore[arg-type]

    assert len(calls) == 1
    request = calls[0][1]
    assert request.tool is ToolName.OVERVIEW
    assert request.arguments == {"year_start": 2025, "year_end": 2025}
    assert len(outcome.items) == 1
    item = outcome.items[0]
    assert item.tool is ToolName.OVERVIEW
    assert item.retrieval_method == "tool"
    assert item.source_ref == "serving://serving_views/overview"
    assert {version.component: version.version for version in item.versions} == {
        "serving": "1.5.0",
        "rules": "1.2.0",
        "motor": "1.3.2",
        "geo": "1.1.0",
    }
    payload = json.loads(item.content)
    assert payload["summary"]["ugs"] == 2
    assert payload["record_count"] == 1


def test_data_worker_fails_closed_without_one_authorized_tool():
    no_tool = EvidenceNeed(
        need_id="need-data-empty",
        source=EvidenceSource.DATA,
        objective="Consulta sem ferramenta definida.",
    )
    blocked_tool = EvidenceNeed(
        need_id="need-data-method",
        source=EvidenceSource.DATA,
        objective="Não converter metodologia em ferramenta de dados.",
        tool_hints=(ToolName.METHODOLOGY,),
    )

    outcome_empty = execute_data_need(plan=_plan(no_tool), need=no_tool, context=object())  # type: ignore[arg-type]
    outcome_blocked = execute_data_need(
        plan=_plan(blocked_tool), need=blocked_tool, context=object()  # type: ignore[arg-type]
    )

    assert outcome_empty.items == ()
    assert outcome_empty.warnings == ("DATA_REQUIRES_EXACTLY_ONE_TOOL_V1:need-data-empty",)
    assert outcome_blocked.items == ()
    assert outcome_blocked.warnings == (
        "DATA_TOOL_NOT_ALLOWED:need-data-method:methodology",
    )


class _RecordingRetriever:
    def __init__(self, hits: list[SearchHit]):
        self.hits = hits
        self.call: dict[str, object] | None = None

    def search(self, query: str, *, limit: int = 5, **filters: object) -> list[SearchHit]:
        self.call = {"query": query, "limit": limit, **filters}
        return self.hits[:limit]


def _normative_hit() -> SearchHit:
    return SearchHit(
        chunk_id="doc-1-chunk-1",
        document_id="doc-1",
        score=0.87,
        text="Trecho governado sobre suprimento de fundos e CPGF.",
        page=7,
        citation="Norma oficial, p. 7",
        source_class=SourceClass.NORMATIVE,
        authority_level=AuthorityLevel.PRIMARY_NORMATIVE,
        scope=CorpusScope.CPGF_CORE,
        temporal_status=TemporalStatus.CURRENT,
        retrieval_default=True,
        source_url="https://example.gov.br/norma",
        retrieval_method="hybrid",
    )


def test_knowledge_worker_applies_evidence_need_filters_without_replanning():
    need = EvidenceNeed(
        need_id="need-knowledge",
        source=EvidenceSource.KNOWLEDGE,
        objective="Recuperar base normativa vigente.",
        query_hint="base normativa do suprimento de fundos",
        scopes=(CorpusScope.CPGF_CORE,),
        temporal_statuses=(TemporalStatus.CURRENT,),
        source_classes=(SourceClass.NORMATIVE,),
        parameters=(EvidenceParameter(name="limit", value=3),),
    )
    retriever = _RecordingRetriever([_normative_hit()])
    outcome = retrieve_knowledge_need(plan=_plan(need), need=need, retriever=retriever)

    assert retriever.call == {
        "query": "base normativa do suprimento de fundos",
        "limit": 3,
        "scopes": {"cpgf_core"},
        "temporal_statuses": {"current"},
        "source_classes": {"normative"},
    }
    assert len(outcome.items) == 1
    item = outcome.items[0]
    assert item.document_id == "doc-1"
    assert item.chunk_id == "doc-1-chunk-1"
    assert item.page == 7
    assert item.authority_level is AuthorityLevel.PRIMARY_NORMATIVE
    assert item.retrieval_method == "hybrid"


def test_knowledge_worker_no_hits_keeps_required_need_unsatisfied():
    need = EvidenceNeed(
        need_id="need-knowledge-empty",
        source=EvidenceSource.KNOWLEDGE,
        objective="Buscar documento inexistente neste fixture.",
        scopes=(CorpusScope.CPGF_CORE,),
    )
    retriever = _RecordingRetriever([])
    bundle = run_evidence_orchestration(_plan(need), knowledge_retriever=retriever)

    assert bundle.items == ()
    assert bundle.is_complete is False
    assert bundle.missing_required_need_ids == ("need-knowledge-empty",)
    assert "KNOWLEDGE_NO_HITS:need-knowledge-empty" in bundle.warnings


def test_web_worker_is_disabled_and_cannot_fake_evidence():
    need = EvidenceNeed(
        need_id="need-web",
        source=EvidenceSource.WEB,
        objective="Consultar atualização externa.",
        freshness_required=True,
    )
    outcome = disabled_web_need(need=need)
    bundle = run_evidence_orchestration(_plan(need))

    assert outcome.items == ()
    assert outcome.warnings == ("WEB_WORKER_DISABLED_V1:need-web",)
    assert bundle.items == ()
    assert bundle.is_complete is False
    assert bundle.missing_required_need_ids == ("need-web",)
    assert bundle.warnings == ("WEB_WORKER_DISABLED_V1:need-web",)


def test_real_graph_uses_knowledge_and_keeps_web_missing():
    knowledge = EvidenceNeed(
        need_id="need-knowledge-real",
        source=EvidenceSource.KNOWLEDGE,
        objective="Recuperar evidência documental.",
        scopes=(CorpusScope.CPGF_CORE,),
        temporal_statuses=(TemporalStatus.CURRENT,),
    )
    web = EvidenceNeed(
        need_id="need-web-real",
        source=EvidenceSource.WEB,
        objective="Complementar com informação atual externa.",
        freshness_required=True,
    )
    retriever = _RecordingRetriever([_normative_hit()])
    bundle = run_evidence_orchestration(_plan(knowledge, web), knowledge_retriever=retriever)

    assert len(bundle.items) == 1
    assert bundle.items[0].source is EvidenceSource.KNOWLEDGE
    assert bundle.satisfied_need_ids == ("need-knowledge-real",)
    assert bundle.missing_required_need_ids == ("need-web-real",)
    assert bundle.is_complete is False
    assert "WEB_WORKER_DISABLED_V1:need-web-real" in bundle.warnings
