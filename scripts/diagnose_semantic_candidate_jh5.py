from __future__ import annotations

import argparse
from pathlib import Path

from cpgf.benchmark.semantic_candidate_jh5_diagnostic import diagnostic_json, load_measurement

DEFAULT_MEASUREMENT = Path(
    "data/evidence/semantic_candidate_jh5_first_measurement_1_0_0.json.gz"
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Recomputa o diagnóstico pós-hoc congelado da candidata B no JH5."
    )
    parser.add_argument("--measurement", type=Path, default=DEFAULT_MEASUREMENT)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    payload = diagnostic_json(load_measurement(args.measurement))
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    else:
        print(payload, end="")


if __name__ == "__main__":
    main()
