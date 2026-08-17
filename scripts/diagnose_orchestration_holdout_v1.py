from __future__ import annotations

import argparse
from pathlib import Path

from cpgf.benchmark.orchestration_holdout_diagnostic_v1 import (
    diagnostic_json,
    load_frozen_measurement,
)

EVIDENCE_PREFIX = "orchestration_holdout_v1_first_measurement_1_0_0.json.gz.b64."
EVIDENCE_DIR = Path("data/evidence")


def _parts() -> list[Path]:
    parts = sorted(EVIDENCE_DIR.glob(f"{EVIDENCE_PREFIX}*"))
    expected = [EVIDENCE_DIR / f"{EVIDENCE_PREFIX}{index:02d}" for index in range(8)]
    if parts != expected:
        raise ValueError("as oito partes congeladas da evidência OH1 são obrigatórias")
    return parts


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Diagnostica offline a primeira medição congelada do OH1 sem executar LLM."
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    measurement = load_frozen_measurement([str(path) for path in _parts()])
    text = diagnostic_json(measurement)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(text, encoding="utf-8")
    print(text, end="")


if __name__ == "__main__":
    main()
