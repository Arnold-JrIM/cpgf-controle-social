from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field, field_validator

from cpgf.ai.retrieval_planner import plan_knowledge_retrieval
from cpgf.ai.router import Route, RouteDecision, route_question
from cpgf.knowledge.models import CorpusScope, TemporalStatus

DOCUMENTARY_ROUTES = (Route.KNOWLEDGE, Route.METHODOLOGY, Route.COMPOSITE)

ROUTE_ONLY_SYSTEM_PROMPT = """
Você é um classificador semântico experimental do projeto CPGF — Controle Social.
Sua única tarefa é escolher a rota documental mais adequada para a pergunta.
Use exclusivamente uma destas três rotas:
- knowledge: normas, guias oficiais, decisões de controle externo ou consulta documental;
- methodology: estudos científicos, métodos analíticos, auditoria, estatística ou literatura acadêmica;
- composite: a pergunta exige combinar evidência normativa/institucional/controle externo com evidência científica ou metodológica.
Não responda ao mérito da pergunta. Não use conhecimento externo para concluir fatos. Apenas classifique a intenção documental.
""".strip()

FULL_PLAN_SYSTEM_PROMPT = """
Você é uma camada experimental de adjudicação semântica do projeto CPGF — Controle Social.
Receberá a pergunta e a proposta produzida pelo fluxo determinístico. Avalie a intenção da pergunta e produza somente uma decisão documental estruturada.
Rotas permitidas:
- knowledge: normas, guias oficiais, decisões de controle externo ou consulta documental;
- methodology: estudos científicos, métodos analíticos, auditoria, estatística ou literatura acadêmica;
- composite: combinação necessária entre evidência normativa/institucional/controle externo e evidência científica/metodológica.
Escopos permitidos:
- cpgf_core: normas, guias e documentos institucionais centrais do CPGF/suprimento de fundos;
- methodology: literatura científica, acadêmica e metodológica;
- control_external: decisões e documentos de controle externo;
- historical: material histórico;
- institutional_mb: material institucional da Marinha do Brasil;
- discovery: fontes ainda em descoberta/catalogação.
Temporalidades permitidas:
- current: referência vigente/operacional atual;
- historical: referência histórica;
- contextual: antecedente ou fonte interpretativa/contextual.
Não responda ao mérito da pergunta, não invente categorias e não execute qualquer ferramenta.
""".strip()

_ROUTE_SCHEMA = {
    "type": "object",
    "properties": {
        "route": {"type": "string", "enum": [route.value for route in DOCUMENTARY_ROUTES]},
        "reason": {"type": "string", "minLength": 1, "maxLength": 280},
    },
    "required": ["route", "reason"],
    "additionalProperties": False,
}

_PLAN_SCHEMA = {
    "type": "object",
    "properties": {
        "route": {"type": "string", "enum": [route.value for route in DOCUMENTARY_ROUTES]},
        "scopes": {
            "type": "array",
            "items": {"type": "string", "enum": [scope.value for scope in CorpusScope]},
            "minItems": 1,
            "maxItems": 6,
        },
        "temporal_statuses": {
            "type": "array",
            "items": {"type": "string", "enum": [status.value for status in TemporalStatus]},
            "minItems": 1,
            "maxItems": 3,
        },
        "reason": {"type": "string", "minLength": 1, "maxLength": 280},
    },
    "required": ["route", "scopes", "temporal_statuses", "reason"],
    "additionalProperties": False,
}


class SemanticRouteOutput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    route: Route
    reason: str = Field(min_length=1, max_length=280)

    @field_validator("route")
    @classmethod
    def validate_route(cls, value: Route) -> Route:
        if value not in DOCUMENTARY_ROUTES:
            raise ValueError("rota fora do universo documental experimental")
        return value


class SemanticPlanOutput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    route: Route
    scopes: tuple[CorpusScope, ...]
    temporal_statuses: tuple[TemporalStatus, ...]
    reason: str = Field(min_length=1, max_length=280)

    @field_validator("route")
    @classmethod
    def validate_route(cls, value: Route) -> Route:
        if value not in DOCUMENTARY_ROUTES:
            raise ValueError("rota fora do universo documental experimental")
        return value

    @field_validator("scopes", "temporal_statuses")
    @classmethod
    def deduplicate_values(cls, values: tuple[object, ...]) -> tuple[object, ...]:
        return tuple(dict.fromkeys(values))


@dataclass(frozen=True)
class SemanticCallMetadata:
    response_id: str | None
    response_model: str | None
    input_tokens: int | None
    output_tokens: int | None
    latency_ms: float


@dataclass(frozen=True)
class SemanticRouteCall:
    output: SemanticRouteOutput
    metadata: SemanticCallMetadata


@dataclass(frozen=True)
class SemanticPlanCall:
    output: SemanticPlanOutput
    metadata: SemanticCallMetadata


class SemanticProvider(Protocol):
    model: str

    def classify_route(self, question: str) -> SemanticRouteCall: ...

    def adjudicate_plan(
        self,
        question: str,
        *,
        deterministic_decision: RouteDecision,
    ) -> SemanticPlanCall: ...


class OpenAIResponsesSemanticProvider:
    """Provider experimental. Não é usado pelo grafo de produção do assistente."""

    def __init__(self, *, model: str = "gpt-5.6", client: object | None = None) -> None:
        if client is None:
            from openai import OpenAI

            client = OpenAI()
        self.client = client
        self.model = model

    @staticmethod
    def _metadata(response: object, elapsed_ms: float) -> SemanticCallMetadata:
        usage = getattr(response, "usage", None)
        return SemanticCallMetadata(
            response_id=getattr(response, "id", None),
            response_model=getattr(response, "model", None),
            input_tokens=getattr(usage, "input_tokens", None) if usage else None,
            output_tokens=getattr(usage, "output_tokens", None) if usage else None,
            latency_ms=elapsed_ms,
        )

    def _structured_response(
        self,
        *,
        instructions: str,
        payload: dict[str, object],
        schema_name: str,
        schema: dict[str, object],
    ) -> tuple[dict[str, object], SemanticCallMetadata]:
        started = time.perf_counter()
        response = self.client.responses.create(
            model=self.model,
            instructions=instructions,
            input=json.dumps(payload, ensure_ascii=False, sort_keys=True),
            store=False,
            text={
                "format": {
                    "type": "json_schema",
                    "name": schema_name,
                    "strict": True,
                    "schema": schema,
                }
            },
        )
        elapsed_ms = (time.perf_counter() - started) * 1000.0
        text = getattr(response, "output_text", "")
        if not text:
            raise ValueError("Resposta estruturada sem output_text")
        return json.loads(text), self._metadata(response, elapsed_ms)

    def classify_route(self, question: str) -> SemanticRouteCall:
        data, metadata = self._structured_response(
            instructions=ROUTE_ONLY_SYSTEM_PROMPT,
            payload={"question": question},
            schema_name="cpgf_semantic_route_v1",
            schema=_ROUTE_SCHEMA,
        )
        return SemanticRouteCall(
            output=SemanticRouteOutput.model_validate(data),
            metadata=metadata,
        )

    def adjudicate_plan(
        self,
        question: str,
        *,
        deterministic_decision: RouteDecision,
    ) -> SemanticPlanCall:
        deterministic_plan = plan_knowledge_retrieval(
            question,
            decision=deterministic_decision,
        )
        data, metadata = self._structured_response(
            instructions=FULL_PLAN_SYSTEM_PROMPT,
            payload={
                "question": question,
                "deterministic_proposal": {
                    "route": deterministic_decision.route.value,
                    "reason": deterministic_decision.reason,
                    "scopes": [scope.value for scope in deterministic_plan.scopes],
                    "temporal_statuses": [
                        status.value for status in deterministic_plan.temporal_statuses
                    ],
                },
            },
            schema_name="cpgf_semantic_plan_v1",
            schema=_PLAN_SCHEMA,
        )
        return SemanticPlanCall(
            output=SemanticPlanOutput.model_validate(data),
            metadata=metadata,
        )


def deterministic_documentary_prediction(question: str) -> SemanticPlanOutput:
    decision = route_question(question)
    plan = plan_knowledge_retrieval(question, decision=decision)
    return SemanticPlanOutput(
        route=decision.route,
        scopes=plan.scopes,
        temporal_statuses=plan.temporal_statuses,
        reason=decision.reason,
    )
