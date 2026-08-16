from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

from cpgf.ai import plan_knowledge_retrieval, route_question
from cpgf.benchmark import joint_holdout_sha256, load_joint_retrieval_holdout
from cpgf.version import KNOWLEDGE_VERSION, RETRIEVAL_PLANNER_VERSION, ROUTER_VERSION

DEFAULT_HOLDOUT = Path("data/benchmarks/joint_retrieval_holdout_v2_0_0.csv")
DEFAULT_MANIFEST = Path("data/manifests/joint_retrieval_holdout_2_0_0.json")


def _git_blob_sha(path: Path) -> str:
    content = path.read_bytes()
    header = f"blob {len(content)}\0".encode()
    return hashlib.sha1(header + content).hexdigest()


def _recall(expected: set[str], predicted: set[str]) -> float:
    if not expected:
        return 1.0
    return len(expected & predicted) / len(expected)


def _precision(expected: set[str], predicted: set[str]) -> float:
    if not predicted:
        return 1.0 if not expected else 0.0
    return len(expected & predicted) / len(predicted)


def _summarize(rows: list[dict[str, object]]) -> dict[str, object]:
    count = len(rows)
    if count == 0:
        return {"cases": 0}
    return {
        "cases": count,
        "route_exact": sum(bool(row["route_exact"]) for row in rows),
        "route_exact_rate": sum(bool(row["route_exact"]) for row in rows) / count,
        "scope_exact": sum(bool(row["scope_exact"]) for row in rows),
        "scope_exact_rate": sum(bool(row["scope_exact"]) for row in rows) / count,
        "temporal_exact": sum(bool(row["temporal_exact"]) for row in rows),
        "temporal_exact_rate": sum(bool(row["temporal_exact"]) for row in rows) / count,
        "joint_exact": sum(bool(row["joint_exact"]) for row in rows),
        "joint_exact_rate": sum(bool(row["joint_exact"]) for row in rows) / count,
        "mean_scope_recall": sum(float(row["scope_recall"]) for row in rows) / count,
        "mean_scope_precision": sum(float(row["scope_precision"]) for row in rows) / count,
        "mean_temporal_recall": sum(float(row["temporal_recall"]) for row in rows) / count,
        "mean_temporal_precision": sum(float(row["temporal_precision"]) for row in rows) / count,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Primeira medição independente do fluxo Router 1.2.0 -> Retrieval Planner 1.1.0. "
            "Não chama LLM, SQL, retriever ou embeddings."
        )
    )
    parser.add_argument("--holdout", type=Path, default=DEFAULT_HOLDOUT)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    suite = load_joint_retrieval_holdout(args.holdout)
    frozen = manifest["frozen_flow"]

    if manifest["status"] != "FROZEN_BEFORE_MEASUREMENT":
        raise ValueError("Primeira medição exige manifesto ainda no estado pré-medição")
    if manifest["measurement"]["first_valid_measurement_run_id"] is not None:
        raise ValueError("Manifesto já registra uma primeira medição válida")
    if joint_holdout_sha256(args.holdout) != manifest["benchmark"]["sha256"]:
        raise ValueError("Benchmark divergiu do SHA congelado")
    if ROUTER_VERSION != frozen["router_version"]:
        raise ValueError("Router divergiu da versão congelada")
    if RETRIEVAL_PLANNER_VERSION != frozen["retrieval_planner_version"]:
        raise ValueError("Planner divergiu da versão congelada")
    if KNOWLEDGE_VERSION != frozen["knowledge_version"]:
        raise ValueError("Knowledge divergiu da versão congelada")
    if _git_blob_sha(Path(str(frozen["router_source"]))) != frozen["router_source_git_blob_sha"]:
        raise ValueError("Blob do Router divergiu do freeze")
    if _git_blob_sha(Path(str(frozen["retrieval_planner_source"]))) != frozen[
        "retrieval_planner_source_git_blob_sha"
    ]:
        raise ValueError("Blob do Planner divergiu do freeze")

    rows: list[dict[str, object]] = []
    by_category: dict[str, list[dict[str, object]]] = defaultdict(list)
    confusion: dict[str, Counter[str]] = defaultdict(Counter)

    for case in suite.cases:
        decision = route_question(case.question)
        plan = plan_knowledge_retrieval(case.question, decision=decision)

        expected_scopes = {scope.value for scope in case.expected_scopes}
        predicted_scopes = {scope.value for scope in plan.scopes}
        expected_temporal = {status.value for status in case.expected_temporal_statuses}
        predicted_temporal = {status.value for status in plan.temporal_statuses}

        route_exact = decision.route == case.expected_route
        scope_exact = expected_scopes == predicted_scopes
        temporal_exact = expected_temporal == predicted_temporal
        joint_exact = route_exact and scope_exact and temporal_exact

        row = {
            "id": case.id,
            "category": case.category.value,
            "question": case.question,
            "expected_route": case.expected_route.value,
            "predicted_route": decision.route.value,
            "route_exact": route_exact,
            "expected_scopes": sorted(expected_scopes),
            "predicted_scopes": sorted(predicted_scopes),
            "scope_exact": scope_exact,
            "scope_recall": _recall(expected_scopes, predicted_scopes),
            "scope_precision": _precision(expected_scopes, predicted_scopes),
            "expected_temporal_statuses": sorted(expected_temporal),
            "predicted_temporal_statuses": sorted(predicted_temporal),
            "temporal_exact": temporal_exact,
            "temporal_recall": _recall(expected_temporal, predicted_temporal),
            "temporal_precision": _precision(expected_temporal, predicted_temporal),
            "joint_exact": joint_exact,
            "expected_trails": list(case.expected_trails),
            "predicted_trail_hints": list(plan.trail_hints),
            "evidence_layers": [layer.value for layer in decision.evidence_layers],
            "router_reason": decision.reason,
            "planner_reason": plan.reason,
        }
        rows.append(row)
        by_category[case.category.value].append(row)
        confusion[case.expected_route.value][decision.route.value] += 1

    summary = _summarize(rows)
    mismatch_ids = {
        "route": [str(row["id"]) for row in rows if not bool(row["route_exact"])],
        "scope": [str(row["id"]) for row in rows if not bool(row["scope_exact"])],
        "temporal": [str(row["id"]) for row in rows if not bool(row["temporal_exact"])],
        "joint": [str(row["id"]) for row in rows if not bool(row["joint_exact"])],
    }

    payload = {
        "artifact": "joint_retrieval_holdout_measurement",
        "version": suite.version,
        "status": "FIRST_VALID_MEASUREMENT_CANDIDATE",
        "benchmark_sha256": joint_holdout_sha256(args.holdout),
        "frozen_flow": {
            "router_version": ROUTER_VERSION,
            "router_source_git_blob_sha": frozen["router_source_git_blob_sha"],
            "retrieval_planner_version": RETRIEVAL_PLANNER_VERSION,
            "retrieval_planner_source_git_blob_sha": frozen[
                "retrieval_planner_source_git_blob_sha"
            ],
            "knowledge_version": KNOWLEDGE_VERSION,
        },
        "primary_metric": "route + scope + temporal exact match",
        "summary": summary,
        "by_category": {
            category: _summarize(category_rows)
            for category, category_rows in sorted(by_category.items())
        },
        "route_confusion_matrix": {
            expected: dict(sorted(predicted.items()))
            for expected, predicted in sorted(confusion.items())
        },
        "mismatch_ids": mismatch_ids,
        "cases": rows,
        "governance": {
            "planner_input_is_question_plus_router_decision_only": True,
            "oracle_used_only_for_post_hoc_comparison": True,
            "retriever_called": False,
            "llm_called": False,
            "sql_executed": False,
            "external_embeddings_called": False,
            "no_operational_rules_modified_for_measurement": True,
        },
    }

    text = json.dumps(payload, ensure_ascii=False, indent=2)
    print(text)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
