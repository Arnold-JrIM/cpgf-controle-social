from __future__ import annotations

import json
from collections import Counter, defaultdict
from statistics import mean

from cpgf.ai.evidence_contracts import EvidenceNeed, EvidenceParameter, EvidenceSource
from cpgf.ai.semantic_orchestrator import (
    OrchestratorProvider,
    PlanningStatus,
    plan_evidence,
)
from cpgf.benchmark.orchestration_holdout_v1 import (
    OrchestrationHoldoutCase,
    OrchestrationHoldoutSuite,
)

ORCHESTRATION_HOLDOUT_MEASUREMENT_VERSION = "1.0.0"


def _parameter_dict(parameters: tuple[EvidenceParameter, ...]) -> dict[str, object]:
    return {
        parameter.name: parameter.model_dump(mode="json")["value"]
        for parameter in parameters
    }


def _need_map(needs: tuple[EvidenceNeed, ...]) -> dict[EvidenceSource, EvidenceNeed]:
    return {need.source: need for need in needs}


def _canonical_signature(prediction: dict[str, object]) -> str:
    stable = {
        "status": prediction["predicted_status"],
        "sources": prediction["predicted_sources"],
        "data_tool": prediction["predicted_data_tool"],
        "data_parameters": prediction["predicted_data_parameters"],
        "knowledge_scopes": prediction["predicted_knowledge_scopes"],
        "knowledge_temporal_statuses": prediction["predicted_knowledge_temporal_statuses"],
        "knowledge_source_classes": prediction["predicted_knowledge_source_classes"],
        "web_parameters": prediction["predicted_web_parameters"],
    }
    return json.dumps(stable, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _predict(question: str, provider: OrchestratorProvider) -> dict[str, object]:
    run = plan_evidence(question, provider=provider)
    metadata = run.metadata
    plan = run.plan
    needs = _need_map(plan.needs) if plan is not None else {}

    data = needs.get(EvidenceSource.DATA)
    knowledge = needs.get(EvidenceSource.KNOWLEDGE)
    web = needs.get(EvidenceSource.WEB)

    predicted = {
        "predicted_status": run.status.value,
        "predicted_sources": sorted(source.value for source in needs),
        "predicted_data_tool": (
            data.tool_hints[0].value if data is not None and len(data.tool_hints) == 1 else None
        ),
        "predicted_data_parameters": _parameter_dict(data.parameters) if data is not None else {},
        "predicted_knowledge_scopes": (
            sorted(scope.value for scope in knowledge.scopes) if knowledge is not None else []
        ),
        "predicted_knowledge_temporal_statuses": (
            sorted(status.value for status in knowledge.temporal_statuses)
            if knowledge is not None
            else []
        ),
        "predicted_knowledge_source_classes": (
            sorted(source_class.value for source_class in knowledge.source_classes)
            if knowledge is not None
            else []
        ),
        "predicted_web_parameters": _parameter_dict(web.parameters) if web is not None else {},
        "schema_valid": run.status is not PlanningStatus.FAILED,
        "warning": run.warning,
        "clarification_question": run.clarification_question,
        "llm_attempted": True,
        "response_id": metadata.response_id if metadata is not None else None,
        "response_model": metadata.response_model if metadata is not None else None,
        "input_tokens": metadata.input_tokens if metadata is not None else None,
        "output_tokens": metadata.output_tokens if metadata is not None else None,
        "latency_ms": metadata.latency_ms if metadata is not None else None,
    }
    predicted["predicted_signature"] = _canonical_signature(predicted)
    return predicted


def _exactness(case: OrchestrationHoldoutCase, prediction: dict[str, object]) -> dict[str, object]:
    expected_sources = {source.value for source in case.expected_sources}
    predicted_sources = set(prediction["predicted_sources"])
    intersection = expected_sources & predicted_sources
    source_precision = len(intersection) / len(predicted_sources) if predicted_sources else 0.0
    source_recall = len(intersection) / len(expected_sources) if expected_sources else 1.0

    expected_data_params = _parameter_dict(case.expected_data_parameters)
    expected_web_params = _parameter_dict(case.expected_web_parameters)

    data_required = EvidenceSource.DATA in case.expected_sources
    knowledge_required = EvidenceSource.KNOWLEDGE in case.expected_sources
    web_required = EvidenceSource.WEB in case.expected_sources

    data_tool_exact = (
        prediction["predicted_data_tool"] == case.expected_data_tool.value
        if data_required and case.expected_data_tool is not None
        else None
    )
    data_arguments_exact = (
        prediction["predicted_data_parameters"] == expected_data_params
        if data_required
        else None
    )
    knowledge_filters_joint_exact = (
        set(prediction["predicted_knowledge_scopes"])
        == {scope.value for scope in case.expected_knowledge_scopes}
        and set(prediction["predicted_knowledge_temporal_statuses"])
        == {status.value for status in case.expected_knowledge_temporal_statuses}
        and set(prediction["predicted_knowledge_source_classes"])
        == {source_class.value for source_class in case.expected_knowledge_source_classes}
        if knowledge_required
        else None
    )
    web_parameters_exact = (
        prediction["predicted_web_parameters"] == expected_web_params
        if web_required
        else None
    )

    status_exact = prediction["predicted_status"] == case.expected_status
    source_set_exact = predicted_sources == expected_sources
    applicable = [status_exact, source_set_exact]
    for value in (
        data_tool_exact,
        data_arguments_exact,
        knowledge_filters_joint_exact,
        web_parameters_exact,
    ):
        if value is not None:
            applicable.append(bool(value))

    return {
        "status_exact": status_exact,
        "source_set_exact": source_set_exact,
        "source_precision": source_precision,
        "source_recall": source_recall,
        "under_routed_sources": sorted(expected_sources - predicted_sources),
        "over_routed_sources": sorted(predicted_sources - expected_sources),
        "data_required": data_required,
        "data_tool_exact": data_tool_exact,
        "data_arguments_exact": data_arguments_exact,
        "knowledge_required": knowledge_required,
        "knowledge_filters_joint_exact": knowledge_filters_joint_exact,
        "web_required": web_required,
        "web_parameters_exact": web_parameters_exact,
        "full_plan_exact": all(applicable),
    }


def _row(
    *,
    repeat: int,
    case: OrchestrationHoldoutCase,
    prediction: dict[str, object],
) -> dict[str, object]:
    return {
        "repeat": repeat,
        "id": case.id,
        "category": case.category.value,
        "question": case.question,
        "expected_status": case.expected_status,
        "expected_sources": sorted(source.value for source in case.expected_sources),
        "expected_data_tool": case.expected_data_tool.value if case.expected_data_tool else None,
        "expected_data_parameters": _parameter_dict(case.expected_data_parameters),
        "expected_knowledge_scopes": sorted(scope.value for scope in case.expected_knowledge_scopes),
        "expected_knowledge_temporal_statuses": sorted(
            status.value for status in case.expected_knowledge_temporal_statuses
        ),
        "expected_knowledge_source_classes": sorted(
            source_class.value for source_class in case.expected_knowledge_source_classes
        ),
        "expected_web_parameters": _parameter_dict(case.expected_web_parameters),
        **prediction,
        **_exactness(case, prediction),
    }


def _rate(rows: list[dict[str, object]], metric: str, *, required: str | None = None) -> float:
    eligible = rows if required is None else [row for row in rows if bool(row[required])]
    if not eligible:
        return 0.0
    return sum(bool(row[metric]) for row in eligible) / len(eligible)


def _summary(rows: list[dict[str, object]]) -> dict[str, object]:
    latencies = [float(row["latency_ms"]) for row in rows if row["latency_ms"] is not None]
    schema_violations = sum(not bool(row["schema_valid"]) for row in rows)
    provider_failures = sum(
        isinstance(row["warning"], str)
        and str(row["warning"]).startswith("ORCHESTRATOR_PROVIDER_FAILED")
        for row in rows
    )
    plan_failures = sum(
        isinstance(row["warning"], str)
        and str(row["warning"]).startswith("ORCHESTRATOR_PLAN_INVALID")
        for row in rows
    )
    return {
        "cases": len(rows),
        "status_exact_rate": _rate(rows, "status_exact"),
        "source_set_exact_rate": _rate(rows, "source_set_exact"),
        "mean_source_precision": mean(float(row["source_precision"]) for row in rows) if rows else 0.0,
        "mean_source_recall": mean(float(row["source_recall"]) for row in rows) if rows else 0.0,
        "data_tool_exact_rate": _rate(rows, "data_tool_exact", required="data_required"),
        "data_arguments_exact_rate": _rate(rows, "data_arguments_exact", required="data_required"),
        "knowledge_filters_joint_exact_rate": _rate(
            rows, "knowledge_filters_joint_exact", required="knowledge_required"
        ),
        "web_parameters_exact_rate": _rate(rows, "web_parameters_exact", required="web_required"),
        "full_plan_exact_rate": _rate(rows, "full_plan_exact"),
        "under_routed_cases": sum(bool(row["under_routed_sources"]) for row in rows),
        "over_routed_cases": sum(bool(row["over_routed_sources"]) for row in rows),
        "schema_violations": schema_violations,
        "provider_failures": provider_failures,
        "plan_failures": plan_failures,
        "clarification_responses": sum(
            row["predicted_status"] == "clarification_required" for row in rows
        ),
        "llm_attempts": sum(bool(row["llm_attempted"]) for row in rows),
        "input_tokens": sum(int(row["input_tokens"] or 0) for row in rows),
        "output_tokens": sum(int(row["output_tokens"] or 0) for row in rows),
        "mean_latency_ms": mean(latencies) if latencies else 0.0,
    }


def _category_summaries(rows: list[dict[str, object]]) -> dict[str, dict[str, object]]:
    grouped: defaultdict[str, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        grouped[str(row["category"])].append(row)
    return {category: _summary(items) for category, items in sorted(grouped.items())}


def evaluate_orchestration_holdout(
    suite: OrchestrationHoldoutSuite,
    *,
    provider: OrchestratorProvider,
    repeats: int = 3,
) -> dict[str, object]:
    if repeats != 3:
        raise ValueError("Orchestration Holdout 1.0.0 exige exatamente três repetições")

    all_rows: list[dict[str, object]] = []
    repetition_summaries: list[dict[str, object]] = []
    repetition_categories: list[dict[str, dict[str, object]]] = []
    for repeat in range(1, repeats + 1):
        rows: list[dict[str, object]] = []
        for case in suite.cases:
            prediction = _predict(case.question, provider)
            row = _row(repeat=repeat, case=case, prediction=prediction)
            rows.append(row)
            all_rows.append(row)
        repetition_summaries.append(_summary(rows))
        repetition_categories.append(_category_summaries(rows))

    signatures: defaultdict[str, list[str]] = defaultdict(list)
    for row in all_rows:
        signatures[str(row["id"])].append(str(row["predicted_signature"]))

    modal_shares: list[float] = []
    identical_cases = 0
    for values in signatures.values():
        most_common = Counter(values).most_common(1)[0][1]
        modal_shares.append(most_common / len(values))
        if most_common == len(values):
            identical_cases += 1

    categories = sorted(repetition_categories[0])
    category_aggregate: dict[str, dict[str, object]] = {}
    for category in categories:
        category_aggregate[category] = {
            "cases_per_repetition": int(repetition_categories[0][category]["cases"]),
            "mean_source_set_exact_rate": mean(
                float(item[category]["source_set_exact_rate"])
                for item in repetition_categories
            ),
            "mean_source_precision": mean(
                float(item[category]["mean_source_precision"])
                for item in repetition_categories
            ),
            "mean_source_recall": mean(
                float(item[category]["mean_source_recall"])
                for item in repetition_categories
            ),
            "mean_full_plan_exact_rate": mean(
                float(item[category]["full_plan_exact_rate"])
                for item in repetition_categories
            ),
        }

    aggregate = {
        "repetitions": len(repetition_summaries),
        "mean_source_set_exact_rate": mean(
            float(item["source_set_exact_rate"]) for item in repetition_summaries
        ),
        "mean_source_precision": mean(
            float(item["mean_source_precision"]) for item in repetition_summaries
        ),
        "mean_source_recall": mean(
            float(item["mean_source_recall"]) for item in repetition_summaries
        ),
        "mean_data_tool_exact_rate": mean(
            float(item["data_tool_exact_rate"]) for item in repetition_summaries
        ),
        "mean_data_arguments_exact_rate": mean(
            float(item["data_arguments_exact_rate"]) for item in repetition_summaries
        ),
        "mean_knowledge_filters_joint_exact_rate": mean(
            float(item["knowledge_filters_joint_exact_rate"])
            for item in repetition_summaries
        ),
        "mean_web_parameters_exact_rate": mean(
            float(item["web_parameters_exact_rate"]) for item in repetition_summaries
        ),
        "mean_full_plan_exact_rate": mean(
            float(item["full_plan_exact_rate"]) for item in repetition_summaries
        ),
        "schema_violations": sum(int(item["schema_violations"]) for item in repetition_summaries),
        "provider_failures": sum(int(item["provider_failures"]) for item in repetition_summaries),
        "plan_failures": sum(int(item["plan_failures"]) for item in repetition_summaries),
        "llm_attempts": sum(int(item["llm_attempts"]) for item in repetition_summaries),
        "input_tokens": sum(int(item["input_tokens"]) for item in repetition_summaries),
        "output_tokens": sum(int(item["output_tokens"]) for item in repetition_summaries),
        "mean_latency_ms": mean(
            float(item["mean_latency_ms"]) for item in repetition_summaries
        ),
    }

    response_models = Counter(
        str(row["response_model"])
        for row in all_rows
        if row["response_model"] is not None
    )

    return {
        "cases": len(suite.cases),
        "requested_repetitions": repeats,
        "repetition_summaries": repetition_summaries,
        "repetition_categories": repetition_categories,
        "aggregate": aggregate,
        "categories": category_aggregate,
        "stability": {
            "mean_modal_share": mean(modal_shares) if modal_shares else 0.0,
            "all_repetitions_identical_cases": identical_cases,
            "cases": len(signatures),
        },
        "response_models": dict(sorted(response_models.items())),
        "rows": all_rows,
        "governance": {
            "orchestrator_only": True,
            "workers_called": False,
            "retriever_called": False,
            "web_search_called": False,
            "sql_executed": False,
            "final_answer_llm_called": False,
            "production_activation": False,
        },
    }


def evaluate_orchestration_acceptance_gate(
    evaluation: dict[str, object],
    rules: dict[str, object],
) -> dict[str, object]:
    aggregate = evaluation["aggregate"]
    stability = evaluation["stability"]
    categories = evaluation["categories"]

    category_checks = {
        category: float(stats["mean_source_set_exact_rate"])
        >= float(rules["minimum_each_category_source_set_exact_rate"])
        for category, stats in categories.items()
    }
    checks = {
        "all_three_repetitions_completed": int(aggregate["repetitions"]) == 3
        and all(int(item["cases"]) == 56 for item in evaluation["repetition_summaries"]),
        "zero_schema_violations": int(aggregate["schema_violations"])
        == int(rules["schema_violations_allowed"]),
        "minimum_mean_evidence_source_set_exact_rate": float(
            aggregate["mean_source_set_exact_rate"]
        )
        >= float(rules["minimum_mean_evidence_source_set_exact_rate"]),
        "minimum_mean_source_precision": float(aggregate["mean_source_precision"])
        >= float(rules["minimum_mean_source_precision"]),
        "minimum_mean_source_recall": float(aggregate["mean_source_recall"])
        >= float(rules["minimum_mean_source_recall"]),
        "minimum_data_tool_exact_rate": float(aggregate["mean_data_tool_exact_rate"])
        >= float(rules["minimum_data_tool_exact_rate"]),
        "minimum_data_arguments_exact_rate": float(
            aggregate["mean_data_arguments_exact_rate"]
        )
        >= float(rules["minimum_data_arguments_exact_rate"]),
        "minimum_knowledge_filters_joint_exact_rate": float(
            aggregate["mean_knowledge_filters_joint_exact_rate"]
        )
        >= float(rules["minimum_knowledge_filters_joint_exact_rate"]),
        "minimum_web_parameters_exact_rate": float(
            aggregate["mean_web_parameters_exact_rate"]
        )
        >= float(rules["minimum_web_parameters_exact_rate"]),
        "minimum_mean_modal_stability": float(stability["mean_modal_share"])
        >= float(rules["minimum_mean_modal_stability"]),
        "minimum_each_category_source_set_exact_rate": all(category_checks.values()),
    }
    return {
        "passed": all(checks.values()),
        "checks": checks,
        "category_checks": category_checks,
        "observed": {
            "mean_evidence_source_set_exact_rate": aggregate["mean_source_set_exact_rate"],
            "mean_source_precision": aggregate["mean_source_precision"],
            "mean_source_recall": aggregate["mean_source_recall"],
            "mean_data_tool_exact_rate": aggregate["mean_data_tool_exact_rate"],
            "mean_data_arguments_exact_rate": aggregate["mean_data_arguments_exact_rate"],
            "mean_knowledge_filters_joint_exact_rate": aggregate[
                "mean_knowledge_filters_joint_exact_rate"
            ],
            "mean_web_parameters_exact_rate": aggregate["mean_web_parameters_exact_rate"],
            "mean_modal_stability": stability["mean_modal_share"],
            "schema_violations": aggregate["schema_violations"],
            "provider_failures": aggregate["provider_failures"],
            "plan_failures": aggregate["plan_failures"],
            "category_mean_source_set_exact_rate": {
                category: stats["mean_source_set_exact_rate"]
                for category, stats in categories.items()
            },
        },
        "rules": rules,
        "interpretation": (
            "PASS no gate prospectivo do Orchestration Holdout 1.0.0"
            if all(checks.values())
            else "FAIL no gate prospectivo; preservar resultado sem tuning retrospectivo no OH1"
        ),
    }
