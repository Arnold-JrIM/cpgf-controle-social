from __future__ import annotations

import argparse
from pathlib import Path

from cpgf.governance.regression import run_full_regression, write_regression_report
from cpgf.settings.paths import OUTPUT_DIR


def _modes(value: str) -> tuple[str, ...]:
    if value == "both":
        return ("baseline", "production")
    return (value,)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Executa a regressão integral T01–T09 contra a baseline congelada."
    )
    parser.add_argument("--input", type=Path, required=True, help="CSV consolidado do CPGF.")
    parser.add_argument(
        "--mode",
        choices=("baseline", "production", "both"),
        default="both",
        help="Identidade do portador a validar. Padrão: both.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=OUTPUT_DIR / "full_regression_report.json",
        help="Arquivo JSON de saída.",
    )
    parser.add_argument(
        "--allow-other-hash",
        action="store_true",
        help=(
            "Permite executar sobre arquivo não canônico. O relatório será marcado "
            "DIAGNOSTIC_ONLY e não valida a baseline."
        ),
    )
    args = parser.parse_args()

    report = run_full_regression(
        args.input,
        modes=_modes(args.mode),
        allow_other_hash=args.allow_other_hash,
    )
    output = write_regression_report(report, args.output)

    print(f"Status: {report['status']}")
    print(f"Base canônica: {report['canonical_input']}")
    print(f"Linhas: {report['input']['rows']}")
    print(f"SHA-256: {report['input']['sha256']}")
    for mode, result in report["modes"].items():
        print(f"\n[{mode}] pass={result['pass']}")
        for check in result["checks"]:
            print(
                f"  {check['trail']}: esperado={check['expected']} "
                f"obtido={check['actual']} delta={check['delta']} pass={check['pass']}"
            )
    print(f"\nRelatório: {output}")

    if report["status"] == "FAIL":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
