from __future__ import annotations

import argparse
import json
from pathlib import Path

from cpgf.benchmark import (
    benchmark_sha256,
    evaluate_retrieval_flow_attribution,
    load_retrieval_benchmark,
)
from cpgf.version import (
    RETRIEVAL_FLOW_DIAGNOSTIC_VERSION,
    RETRIEVAL_PLANNER_HOLDOUT_VERSION,
    RETRIEVAL_PLANNER_VERSION,
    ROUTER_VERSION,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Decompõe post-hoc a contribuição do Router 1.1.0 e do Retrieval Planner 1.0.0 "
            "nos resultados do Retrieval Planner Holdout 1.0.0."
        )
    )
    parser.add_argument(
        "--holdout",
        type=Path,
        default=Path("data/benchmarks/retrieval_planner_holdout_v1_0_0.csv"),
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    suite = load_retrieval_benchmark(args.holdout)
    diagnostic = evaluate_retrieval_flow_attribution(suite)
    payload: dict[str, object] = {
        "artifact": "retrieval_flow_attribution_diagnostic",
        "version": RETRIEVAL_FLOW_DIAGNOSTIC_VERSION,
        "router_version": ROUTER_VERSION,
        "planner_version": RETRIEVAL_PLANNER_VERSION,
        "holdout_version": RETRIEVAL_PLANNER_HOLDOUT_VERSION,
        "holdout_path": str(args.holdout),
        "holdout_sha256": benchmark_sha256(args.holdout),
        "diagnostic": diagnostic,
        "interpretation": (
            "Diagnóstico post-hoc sobre um holdout já conhecido. O sweep contrafactual mantém "
            "pergunta e oráculo fixos e altera apenas a rota fornecida ao Planner. O resultado "
            "serve para atribuição de falhas entre camadas e não constitui nova medição de "
            "generalização nem justificativa automática para tuning."
        ),
    }

    text = json.dumps(payload, ensure_ascii=False, indent=2)
    print(text)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
