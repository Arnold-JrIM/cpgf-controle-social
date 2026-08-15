from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from cpgf.ai.contracts import ToolRequest, ToolResult
from cpgf.ai.router import EvidenceLayer, Route


class AssistantState(BaseModel):
    """Estado serializável e sem segredos para futura orquestração LangGraph."""

    model_config = ConfigDict(extra="forbid")
    question: str
    route: Route
    route_reason: str
    evidence_layers: tuple[EvidenceLayer, ...] = ()
    tool_request: ToolRequest | None = None
    tool_result: ToolResult | None = None
    notices: list[str] = Field(default_factory=list)
    llm_called: bool = False
