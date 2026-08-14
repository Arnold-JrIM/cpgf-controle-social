from __future__ import annotations

import argparse
import json
from pathlib import Path

from cpgf.preprocessing.identity_gate import (
    compare_t03,
    compare_t04,
    compare_t05_affected,
    compare_t07,
    identity_universe,
    load_gate_frame,
    sha256_file,
    t03_sigilo_check,
)

EXPECTED_SHA256 = "300789f9bd866f313df4ca5ee5dfca7234050ef2452443b61b1e58425ca0997b"


def main() -> None:
    parser = argparse.ArgumentParser(description="Gate de identidade do portador do CPGF.")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("data/outputs/portador_identity_gate.json"))
    parser.add_argument("--allow-other-hash", action="store_true")
    args = parser.parse_args()

    file_hash = sha256_file(args.input)
    if file_hash != EXPECTED_SHA256 and not args.allow_other_hash:
        raise SystemExit(
            "SHA-256 diferente da baseline congelada. "
            "Use --allow-other-hash apenas para diagnóstico explícito de outra versão."
        )

    frame = load_gate_frame(args.input)
    t03 = compare_t03(frame)
    t04 = compare_t04(frame)
    result = {
        "metadata": {
            "input": str(args.input),
            "sha256": file_hash,
            "n_rows": len(frame),
            "baseline_rules": "1.2.0",
            "baseline_motor": "1.3.2",
            "baseline_preparation": "1.0.0",
        },
        "identity_universe": identity_universe(frame),
        "trails": {
            "T03": {"baseline": t03.baseline, "candidate": t03.candidate, "delta": t03.delta},
            "T04": {"baseline": t04.baseline, "candidate": t04.candidate, "delta": t04.delta},
            "T05": compare_t05_affected(frame),
            "T07": compare_t07(frame),
        },
        "t03_sigilo_check": t03_sigilo_check(frame),
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"Relatório: {args.output}")


if __name__ == "__main__":
    main()
