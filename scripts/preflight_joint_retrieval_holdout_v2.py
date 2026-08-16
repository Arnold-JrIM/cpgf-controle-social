from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from cpgf.benchmark.joint_retrieval import (
    joint_holdout_sha256,
    load_joint_retrieval_holdout,
    validate_joint_holdout_against_catalog,
    validate_joint_holdout_novelty,
)
from cpgf.version import KNOWLEDGE_VERSION, RETRIEVAL_PLANNER_VERSION, ROUTER_VERSION

DEFAULT_HOLDOUT = Path("data/benchmarks/joint_retrieval_holdout_v2_0_0.csv")
DEFAULT_MANIFEST = Path("data/manifests/joint_retrieval_holdout_2_0_0.json")
DEFAULT_CATALOG = Path("data/knowledge/source_catalog.json")
DEFAULT_PRIOR = (
    Path("data/benchmarks/knowledge_retrieval_v1_0_0.csv"),
    Path("data/benchmarks/retrieval_planner_holdout_v1_0_0.csv"),
    Path("data/benchmarks/assistant_v1_0_0.csv"),
    Path("data/benchmarks/assistant_router_holdout_v1_0_0.csv"),
    Path("data/benchmarks/assistant_router_holdout_v2_0_0.csv"),
)
_ALLOWED_STATES = {"FROZEN_BEFORE_MEASUREMENT", "MEASURED_INDEPENDENT"}


def _git_blob_sha(path: Path) -> str:
    content = path.read_bytes()
    header = f"blob {len(content)}\0".encode()
    return hashlib.sha1(header + content).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Executa preflight estrutural/novidade do Joint Retrieval Holdout 2.0.0. "
            "Antes da medição exige o fluxo corrente congelado; depois da medição preserva "
            "o freeze histórico sem bloquear evolução operacional."
        )
    )
    parser.add_argument("--holdout", type=Path, default=DEFAULT_HOLDOUT)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    suite = load_joint_retrieval_holdout(args.holdout)
    actual_sha = joint_holdout_sha256(args.holdout)

    expected_sha = str(manifest["benchmark"]["sha256"])
    if actual_sha != expected_sha:
        raise ValueError(f"SHA do holdout divergiu do freeze: {actual_sha} != {expected_sha}")
    if manifest["status"] not in _ALLOWED_STATES:
        raise ValueError(f"Estado inválido do manifesto: {manifest['status']}")

    measurement = manifest["measurement"]
    if manifest["status"] == "FROZEN_BEFORE_MEASUREMENT":
        if measurement["first_valid_measurement_run_id"] is not None:
            raise ValueError("Manifesto pré-medição já contém run de primeira medição")
    else:
        required = (
            "first_valid_measurement_run_id",
            "first_valid_measurement_head_sha",
            "first_valid_measurement_result",
        )
        if any(measurement[field] is None for field in required):
            raise ValueError("Manifesto medido não registra a primeira medição completa")

    frozen = manifest["frozen_flow"]
    current_router_blob = _git_blob_sha(Path(str(frozen["router_source"])))
    current_planner_blob = _git_blob_sha(Path(str(frozen["retrieval_planner_source"])))
    current_flow_matches_frozen = (
        ROUTER_VERSION == frozen["router_version"]
        and RETRIEVAL_PLANNER_VERSION == frozen["retrieval_planner_version"]
        and KNOWLEDGE_VERSION == frozen["knowledge_version"]
        and current_router_blob == frozen["router_source_git_blob_sha"]
        and current_planner_blob == frozen["retrieval_planner_source_git_blob_sha"]
    )

    if manifest["status"] == "FROZEN_BEFORE_MEASUREMENT" and not current_flow_matches_frozen:
        raise ValueError("Fluxo corrente divergiu do freeze antes da primeira medição")
    if KNOWLEDGE_VERSION != frozen["knowledge_version"]:
        raise ValueError("Knowledge corrente divergiu da versão congelada")

    catalog = validate_joint_holdout_against_catalog(suite, args.catalog)
    novelty = validate_joint_holdout_novelty(suite, DEFAULT_PRIOR)

    payload = {
        "artifact": "joint_retrieval_holdout_preflight",
        "version": suite.version,
        "status": "PASS",
        "manifest_state": manifest["status"],
        "benchmark_sha256": actual_sha,
        "frozen_commit": manifest["benchmark"]["frozen_commit"],
        "frozen_flow": {
            "router_version": frozen["router_version"],
            "router_source_git_blob_sha": frozen["router_source_git_blob_sha"],
            "retrieval_planner_version": frozen["retrieval_planner_version"],
            "retrieval_planner_source_git_blob_sha": frozen[
                "retrieval_planner_source_git_blob_sha"
            ],
            "knowledge_version": frozen["knowledge_version"],
        },
        "current_flow": {
            "router_version": ROUTER_VERSION,
            "router_source_git_blob_sha": current_router_blob,
            "retrieval_planner_version": RETRIEVAL_PLANNER_VERSION,
            "retrieval_planner_source_git_blob_sha": current_planner_blob,
            "knowledge_version": KNOWLEDGE_VERSION,
            "matches_frozen_flow": current_flow_matches_frozen,
        },
        "catalog_validation": catalog,
        "novelty_validation": novelty,
        "governance": {
            "router_called": False,
            "retrieval_planner_called": False,
            "llm_called": False,
            "sql_executed": False,
            "external_embeddings_called": False,
            "measurement_performed_by_this_preflight": False,
            "pre_measurement_requires_current_flow_match": True,
            "post_measurement_allows_operational_versions_to_advance": True,
            "historical_frozen_flow_preserved_from_manifest": True,
        },
    }
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    print(text)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
