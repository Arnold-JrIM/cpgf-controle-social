from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from cpgf.benchmark.joint_retrieval_attribution_v4 import (
    evaluate_joint_retrieval_flow_attribution_v4,
)
from cpgf.benchmark.joint_retrieval_v4 import (
    joint_holdout_v4_sha256,
    load_joint_retrieval_holdout_v4,
)
from cpgf.version import RETRIEVAL_PLANNER_VERSION, ROUTER_VERSION

DEFAULT_HOLDOUT = Path("data/benchmarks/joint_retrieval_holdout_v4_0_0.csv")
DEFAULT_HOLDOUT_MANIFEST = Path("data/manifests/joint_retrieval_holdout_4_0_0.json")
ROUTER_SOURCE = Path("src/cpgf/ai/router.py")
PLANNER_SOURCE = Path("src/cpgf/ai/retrieval_planner.py")


def _git_blob_sha(path: Path) -> str:
    content = path.read_bytes()
    header = f"blob {len(content)}\0".encode()
    return hashlib.sha1(header + content).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Diagnóstico post-hoc contrafactual Router x Retrieval Planner sobre o "
            "Joint Holdout 4.0 já medido. Não faz tuning nem nova alegação de generalização."
        )
    )
    parser.add_argument("--holdout", type=Path, default=DEFAULT_HOLDOUT)
    parser.add_argument("--holdout-manifest", type=Path, default=DEFAULT_HOLDOUT_MANIFEST)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    manifest = json.loads(args.holdout_manifest.read_text(encoding="utf-8"))
    if manifest["status"] != "MEASURED_INDEPENDENT":
        raise ValueError("Diagnóstico exige Joint Holdout 4.0 já medido e congelado")
    if not manifest["governance"]["holdout_is_known_after_first_measurement"]:
        raise ValueError("JH4 precisa estar explicitamente marcado como conhecido")
    if joint_holdout_v4_sha256(args.holdout) != manifest["benchmark"]["sha256"]:
        raise ValueError("Benchmark divergiu do SHA preservado no Joint Holdout 4.0")

    frozen = manifest["frozen_flow"]
    if ROUTER_VERSION != frozen["router_version"]:
        raise ValueError("Router corrente divergiu da versão da medição independente")
    if RETRIEVAL_PLANNER_VERSION != frozen["retrieval_planner_version"]:
        raise ValueError("Planner corrente divergiu da versão da medição independente")
    if _git_blob_sha(ROUTER_SOURCE) != frozen["router_source_git_blob_sha"]:
        raise ValueError("Blob do Router divergiu da medição independente do JH4")
    if _git_blob_sha(PLANNER_SOURCE) != frozen["retrieval_planner_source_git_blob_sha"]:
        raise ValueError("Blob do Planner divergiu da medição independente do JH4")

    suite = load_joint_retrieval_holdout_v4(args.holdout)
    result = evaluate_joint_retrieval_flow_attribution_v4(suite)

    measured = manifest["measurement"]["result"]
    summary = measured["summary"]
    descriptive = measured["descriptive_layer_decomposition"]
    if result["cases"] != summary["cases"]:
        raise AssertionError("Diagnóstico não reproduziu a cardinalidade do JH4")
    if result["actual_joint_exact"] != summary["joint_exact"]:
        raise AssertionError("Diagnóstico não reproduziu os passes independentes do JH4")
    if result["actual_joint_failures"] != len(measured["mismatch_ids"]["joint"]):
        raise AssertionError("Diagnóstico não reproduziu as falhas conjuntas do JH4")

    expected_descriptive = {
        "route_wrong_filters_exact": descriptive["route_wrong_filters_exact"],
        "route_exact_filters_wrong": descriptive["route_exact_filters_wrong"],
        "route_wrong_filters_wrong": descriptive["route_wrong_filters_wrong"],
        "clean_passes": descriptive["pass"],
    }
    if result["observed_layer_mismatch_reproduction"] != expected_descriptive:
        raise AssertionError(
            "Diagnóstico não reproduziu a decomposição descritiva congelada no JH4"
        )

    first = manifest["measurement"]["first_valid_measurement"]
    payload = {
        "artifact": "joint_retrieval_flow_attribution_v4_diagnostic",
        "version": "1.0.0",
        "status": "POST_HOC_DIAGNOSTIC",
        "source_independent_measurement": {
            "joint_holdout_version": manifest["version"],
            "measurement_run_id": first["run_id"],
            "measurement_head_sha": first["head_sha"],
            "joint_exact": summary["joint_exact"],
            "joint_failures": len(measured["mismatch_ids"]["joint"]),
            "holdout_already_known_before_this_diagnostic": True,
        },
        "frozen_flow": {
            "router_version": ROUTER_VERSION,
            "router_source_git_blob_sha": frozen["router_source_git_blob_sha"],
            "retrieval_planner_version": RETRIEVAL_PLANNER_VERSION,
            "retrieval_planner_source_git_blob_sha": frozen[
                "retrieval_planner_source_git_blob_sha"
            ],
        },
        "result": result,
    }

    text = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)
    print(text)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
