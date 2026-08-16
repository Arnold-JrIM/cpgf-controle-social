from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from cpgf.ai import route_question
from cpgf.benchmark import evaluate_routing, load_benchmark, load_joint_retrieval_holdout
from cpgf.benchmark.joint_retrieval_v3 import load_joint_retrieval_holdout_v3
from cpgf.version import RETRIEVAL_PLANNER_VERSION, ROUTER_VERSION

DEVELOPMENT = Path("data/benchmarks/assistant_v1_0_0.csv")
ROUTER_HOLDOUT_V1 = Path("data/benchmarks/assistant_router_holdout_v1_0_0.csv")
ROUTER_HOLDOUT_V2 = Path("data/benchmarks/assistant_router_holdout_v2_0_0.csv")
JH2 = Path("data/benchmarks/joint_retrieval_holdout_v2_0_0.csv")
JH3 = Path("data/benchmarks/joint_retrieval_holdout_v3_0_0.csv")
ROUTER_MANIFEST = Path("data/manifests/assistant_router_1_4_0.json")
ROUTER_SOURCE = Path("src/cpgf/ai/router.py")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git_blob_sha(path: Path) -> str:
    content = path.read_bytes()
    return hashlib.sha1(f"blob {len(content)}\0".encode() + content).hexdigest()


def _routing_result(path: Path) -> dict[str, object]:
    result = evaluate_routing(load_benchmark(path))
    return {
        "path": str(path),
        "sha256": _sha256(path),
        "summary": result["summary"],
        "errors": [row for row in result["cases"] if not bool(row["exact"])],
    }


def _route_result_v2() -> dict[str, object]:
    suite = load_joint_retrieval_holdout(JH2)
    rows = []
    for case in suite.cases:
        decision = route_question(case.question)
        exact = decision.route == case.expected_route
        rows.append({"id": case.id, "route_exact": exact})
    return {
        "cases": len(rows),
        "route_exact": sum(bool(row["route_exact"]) for row in rows),
        "route_error_ids": [row["id"] for row in rows if not bool(row["route_exact"])],
    }


def _route_result_v3() -> dict[str, object]:
    suite = load_joint_retrieval_holdout_v3(JH3)
    rows = []
    for case in suite.cases:
        decision = route_question(case.question)
        exact = decision.route == case.expected_route
        rows.append({"id": case.id, "route_exact": exact})
    return {
        "cases": len(rows),
        "route_exact": sum(bool(row["route_exact"]) for row in rows),
        "route_error_ids": [row["id"] for row in rows if not bool(row["route_exact"])],
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Preserva a evidência do Router 1.4.0 e verifica apenas seu roteamento com "
            "o Planner operacional corrente livre para evoluir."
        )
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    manifest = json.loads(ROUTER_MANIFEST.read_text(encoding="utf-8"))
    current_router_blob = _git_blob_sha(ROUTER_SOURCE)
    if ROUTER_VERSION != manifest["router_version"]:
        raise ValueError("Versão corrente do Router divergiu do manifesto 1.4")
    if current_router_blob != manifest["router_source_git_blob_sha"]:
        raise ValueError("Blob corrente do Router divergiu do manifesto 1.4")

    payload = {
        "artifact": "router_v1_4_historical_regression",
        "status": "KNOWN_REGRESSION_ONLY",
        "router_version": ROUTER_VERSION,
        "router_source_git_blob_sha": current_router_blob,
        "historical_planner_version_held_fixed": manifest["planner_version_held_fixed"],
        "current_planner_version": RETRIEVAL_PLANNER_VERSION,
        "routing_sets": {
            "development": _routing_result(DEVELOPMENT),
            "router_holdout_v1": _routing_result(ROUTER_HOLDOUT_V1),
            "router_holdout_v2": _routing_result(ROUTER_HOLDOUT_V2),
        },
        "joint_holdout_v2_route_regression": _route_result_v2(),
        "joint_holdout_v3_route_regression": _route_result_v3(),
        "historical_joint_holdout_v3_with_planner_1_2": manifest["known_regression_sets"][
            "joint_holdout_v3"
        ],
        "governance": {
            "router_regression_recomputed_with_current_router": True,
            "historical_joint_filters_recomputed_with_current_planner": False,
            "historical_router_manifest_preserved": True,
            "current_planner_may_advance": True,
            "new_generalization_claim": False,
            "llm_called": False,
            "sql_executed": False,
            "retriever_called": False,
            "external_embeddings_called": False,
        },
    }
    args.output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
