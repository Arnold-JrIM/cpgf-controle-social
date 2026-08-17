from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Protocol

from cpgf.ai.contracts import ToolName, ToolRequest
from cpgf.ai.evidence_contracts import (
    EvidenceItem,
    EvidenceNeed,
    EvidenceParameter,
    EvidencePlan,
    EvidenceSource,
    EvidenceVersion,
)
from cpgf.ai.tools.registry import execute_tool
from cpgf.dashboard.data import DashboardDataContext
from cpgf.knowledge.models import SearchHit

EVIDENCE_WORKER_VERSION = "1.0.0"
DEFAULT_KNOWLEDGE_LIMIT = 5
_MAX_CONTENT_CHARS = 19_500

DATA_EVIDENCE_TOOLS = frozenset(
    {
        ToolName.OVERVIEW,
        ToolName.TRAIL_PREVALENCE,
        ToolName.TOP_UGS,
        ToolName.TOP_SUPPLIERS,
        ToolName.TERRITORIAL_METRIC,
        ToolName.TERRITORIAL_UG_CONTEXT,
    }
)


class KnowledgeSearcher(Protocol):
    def search(self, query: str, *, limit: int = 5, **filters: object) -> list[SearchHit]: ...


@dataclass(frozen=True)
class WorkerOutcome:
    items: tuple[EvidenceItem, ...] = ()
    warnings: tuple[str, ...] = ()


def _stable_id(prefix: str, *parts: str) -> str:
    digest = hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:20]
    return f"ev-{prefix}-{digest}"


def _parameter_dict(parameters: tuple[EvidenceParameter, ...]) -> dict[str, object]:
    return {parameter.name: parameter.value for parameter in parameters}


def _bounded_tool_content(*, summary: dict[str, object], records: list[dict[str, object]]) -> str:
    kept = list(records)
    payload = {
        "summary": summary,
        "record_count": len(records),
        "records_returned": len(kept),
        "records": kept,
    }
    text = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
    while len(text) > _MAX_CONTENT_CHARS and kept:
        kept.pop()
        payload["records_returned"] = len(kept)
        payload["records"] = kept
        text = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
    if len(text) <= _MAX_CONTENT_CHARS:
        return text
    fallback = {
        "record_count": len(records),
        "records_returned": 0,
        "records_omitted_for_bundle_size": True,
        "summary": summary,
    }
    text = json.dumps(fallback, ensure_ascii=False, sort_keys=True, default=str)
    return text[:_MAX_CONTENT_CHARS]


def execute_data_need(
    *,
    plan: EvidencePlan,
    need: EvidenceNeed,
    context: DashboardDataContext | None,
) -> WorkerOutcome:
    """Executa uma única ferramenta DATA autorizada, sem SQL livre nem fallback implícito."""
    if need.source is not EvidenceSource.DATA:
        raise ValueError("execute_data_need aceita somente EvidenceSource.DATA")
    if context is None:
        return WorkerOutcome(warnings=(f"DATA_CONTEXT_UNAVAILABLE:{need.need_id}",))
    if len(need.tool_hints) != 1:
        return WorkerOutcome(
            warnings=(f"DATA_REQUIRES_EXACTLY_ONE_TOOL_V1:{need.need_id}",)
        )

    tool = need.tool_hints[0]
    if tool not in DATA_EVIDENCE_TOOLS:
        return WorkerOutcome(warnings=(f"DATA_TOOL_NOT_ALLOWED:{need.need_id}:{tool.value}",))

    arguments = _parameter_dict(need.parameters)
    try:
        result = execute_tool(context, ToolRequest(tool=tool, arguments=arguments))
    except Exception as exc:  # fronteira: falha de execução vira ausência explícita de evidência
        return WorkerOutcome(
            warnings=(f"DATA_EXECUTION_FAILED:{need.need_id}:{tool.value}:{type(exc).__name__}",)
        )

    provenance = result.provenance
    versions = (
        EvidenceVersion(component="serving", version=provenance.serving_version),
        EvidenceVersion(component="rules", version=provenance.rules_version),
        EvidenceVersion(component="motor", version=provenance.motor_version),
        EvidenceVersion(component="geo", version=provenance.geo_version),
    )
    content = _bounded_tool_content(summary=result.summary, records=result.records)
    item = EvidenceItem(
        evidence_id=_stable_id("data", need.need_id, tool.value, plan.question),
        need_id=need.need_id,
        source=EvidenceSource.DATA,
        content=content,
        citation=f"Serving read-only — {tool.value}",
        source_ref=f"serving://{provenance.source}/{tool.value}",
        tool=tool,
        parameters=need.parameters,
        versions=versions,
        retrieval_method="tool",
    )
    warnings = tuple(f"DATA_TOOL_WARNING:{need.need_id}:{warning}" for warning in result.warnings)
    return WorkerOutcome(items=(item,), warnings=warnings)


def _knowledge_limit(need: EvidenceNeed) -> tuple[int | None, tuple[str, ...]]:
    parameters = _parameter_dict(need.parameters)
    unknown = sorted(set(parameters) - {"limit"})
    if unknown:
        return None, (f"KNOWLEDGE_UNKNOWN_PARAMETERS:{need.need_id}:{','.join(unknown)}",)
    raw = parameters.get("limit", DEFAULT_KNOWLEDGE_LIMIT)
    if isinstance(raw, bool) or not isinstance(raw, int) or not 1 <= raw <= 20:
        return None, (f"KNOWLEDGE_INVALID_LIMIT:{need.need_id}",)
    return raw, ()


def retrieve_knowledge_need(
    *,
    plan: EvidencePlan,
    need: EvidenceNeed,
    retriever: KnowledgeSearcher | None,
) -> WorkerOutcome:
    """Recupera chunks do corpus governado usando filtros já declarados no EvidenceNeed."""
    if need.source is not EvidenceSource.KNOWLEDGE:
        raise ValueError("retrieve_knowledge_need aceita somente EvidenceSource.KNOWLEDGE")
    if retriever is None:
        return WorkerOutcome(warnings=(f"KNOWLEDGE_RETRIEVER_UNAVAILABLE:{need.need_id}",))

    limit, warnings = _knowledge_limit(need)
    if limit is None:
        return WorkerOutcome(warnings=warnings)

    query = need.query_hint or plan.question
    filters: dict[str, object] = {}
    if need.scopes:
        filters["scopes"] = {scope.value for scope in need.scopes}
    if need.temporal_statuses:
        filters["temporal_statuses"] = {status.value for status in need.temporal_statuses}
    if need.source_classes:
        filters["source_classes"] = {source_class.value for source_class in need.source_classes}

    try:
        hits = retriever.search(query, limit=limit, **filters)
    except Exception as exc:
        return WorkerOutcome(
            warnings=(f"KNOWLEDGE_RETRIEVAL_FAILED:{need.need_id}:{type(exc).__name__}",)
        )

    items = tuple(
        EvidenceItem(
            evidence_id=_stable_id("knowledge", need.need_id, hit.document_id, hit.chunk_id),
            need_id=need.need_id,
            source=EvidenceSource.KNOWLEDGE,
            content=hit.text,
            citation=hit.citation,
            source_ref=f"knowledge://{hit.document_id}/{hit.chunk_id}",
            document_id=hit.document_id,
            chunk_id=hit.chunk_id,
            page=hit.page,
            source_class=hit.source_class,
            authority_level=hit.authority_level,
            scope=hit.scope,
            temporal_status=hit.temporal_status,
            retrieval_score=hit.score,
            retrieval_method=hit.retrieval_method,
            source_url=hit.source_url,
        )
        for hit in hits
    )
    if not items:
        return WorkerOutcome(warnings=(f"KNOWLEDGE_NO_HITS:{need.need_id}",))
    return WorkerOutcome(items=items)


def disabled_web_need(*, need: EvidenceNeed) -> WorkerOutcome:
    """Falha fechada enquanto o Web/Freshness Worker ainda não foi governado."""
    if need.source is not EvidenceSource.WEB:
        raise ValueError("disabled_web_need aceita somente EvidenceSource.WEB")
    return WorkerOutcome(warnings=(f"WEB_WORKER_DISABLED_V1:{need.need_id}",))
