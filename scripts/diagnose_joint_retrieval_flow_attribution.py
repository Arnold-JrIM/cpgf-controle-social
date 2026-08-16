from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from cpgf.benchmark import (
    evaluate_joint_retrieval_flow_attribution,
    joint_holdout_sha256,
    load_joint_retrieval_holdout,
)
from cpgf.version import RETRIEVAL_PLANNER_VERSION, ROUTER_VERSION

DEFAULT_HOLDOUT = Path("data/benchmarks/joint_retrieval_holdout_v2_0_0.csv")
DEFAULT_HOLDOUT_MANIFEST = Path("data/manifests/joint_retrieval_holdout_2_0_0.json")


def _git_blob_sha(path: Path) -> str:
    content = path.read_bytes()
    header = f"blob {len(content)}\0".encode()
    return hashlib.sha1(header + content).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Diagnóstico post-hoc contrafactual Router x Retrieval Planner sobre o "
            "Joint Holdout 2.0 já medido. Não faz tuning nem nova alegação de generalização."
        )
    )
    parser.add_argument("--holdout", type=Path, default=DEFAULT_HOLDOUT)
    parser.add_argument("--holdout-manifest", type=Path, default=DEFAULT_HOLDOUT_MANIFEST)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    manifest = json.loads(args.holdout_manifest.read_text(encoding="utf-8"))
    if manifest["status"] != "MEASURED_INDEPENDENT":
        raise ValueError("Diagnóstico exige Joint Holdout 2.0 já medido e congelado")
    if not manifest["governance"]["holdout_becomes_known_after_first_measurement"]:
        raise ValueError("Holdout precisa estar explicitamente marcado como conhecido")
    if joint_holdout_sha256(args.holdout) != manifest["benchmark"]["sha256"]:
        raise ValueError("Benchmark divergiu do SHA preservado no Joint Holdout 2.0")

    frozen = manifest["frozen_flow"]
    if ROUTER_VERSION != frozen["router_version"]:
        raise ValueError("Router corrente divergiu da versão da medição independente")
    if RETRIEVAL_PLANNER_VERSION != frozen["retrieval_planner_version"]:
        raise ValueError("Planner corrente divergiu da versão da medição independente")
    if _git_blob_sha(Path(str(frozen["router_source"]))) != frozen["router_source_git_blob_sha"]:
        raise ValueError("Blob do Router divergiu da medição independente")
    if _git_blob_sha(Path(str(frozen["retrieval_planner_source"]))) != frozen[
        "retrieval_planner_source_git_blob_sha"
    ]:
        raise ValueError("Blob do Planner divergiu da medição independente")

    suite = load_joint_retrieval_holdout(args.holdout)
    result = evaluate_joint_retrieval_flow_attribution(suite)

    measured = manifest["measurement"]
    baseline = measured["first_valid_measurement_result"]
    descriptive = measured["observed_layer_mismatch_decomposition"]
    if result["cases"] != baseline["cases"]:
        raise AssertionError("Diagnóstico não reproduziu a cardinalidade da primeira medição")
    if result["actual_joint_exact"] != baseline["joint_exact"]:
        raise AssertionError("Diagnóstico não reproduziu os passes da primeira medição")
    if result["actual_joint_failures"] != len(measured["mismatch_ids"]["joint"]):
        raise AssertionError("Diagnóstico não reproduziu as falhas conjuntas da primeira medição")

    reproduced = result["observed_layer_mismatch_reproduction"]
    expected_descriptive = {
        "route_wrong_filters_exact": descriptive["route_only_mismatch"],
        "route_exact_filters_wrong": descriptive["planner_filter_only_mismatch"],
        "route_wrong_filters_wrong": descriptive["route_and_planner_filter_mismatch"],
        "clean_passes": descriptive["clean_passes"],
    }
    if reproduced != expected_descriptive:
        raise AssertionError(
            "Diagnóstico não reproduziu a decomposição descritiva preservada no PR #42"
        )

    payload = {
        "artifact": "joint_retrieval_flow_attribution_diagnostic",
        "version": "1.0.0",
        "status": "POST_HOC_DIAGNOSTIC",
        "source_independent_measurement": {
            "holdout_version": manifest["version"],
            "measurement_run_id": measured["first_valid_measurement_run_id"],
            "measurement_head_sha": measured["first_valid_measurement_head_sha"],
            "joint_exact": baseline["joint_exact"],
            "joint_failures": len(measured["mismatch_ids"]["joint"]),
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

    text = json.dumps(payload, ensure_ascii=False, indent=2)
    print(text)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
