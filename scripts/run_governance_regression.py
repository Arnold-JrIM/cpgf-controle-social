from __future__ import annotations

import argparse
from pathlib import Path

from cpgf.governance.governance_regression import (
    run_governance_regression,
    write_governance_regression_report,
)
from cpgf.settings.paths import OUTPUT_DIR


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Executa a regressão integral da Governança 1.3.2."
    )
    parser.add_argument("--input", type=Path, required=True, help="CSV canônico do CPGF.")
    parser.add_argument(
        "--output",
        type=Path,
        default=OUTPUT_DIR / "governance_regression_report.json",
        help="Relatório JSON sem dados transacionais brutos.",
    )
    parser.add_argument(
        "--contract",
        type=Path,
        default=None,
        help=(
            "Manifesto congelado. O padrão é "
            "data/manifests/governance_regression_1_3_2.json."
        ),
    )
    parser.add_argument(
        "--bootstrap",
        action="store_true",
        help="Gera a assinatura canônica sem exigir manifesto prévio.",
    )
    args = parser.parse_args()

    report = run_governance_regression(
        args.input,
        contract_path=args.contract,
        bootstrap=args.bootstrap,
    )
    output = write_governance_regression_report(report, args.output)

    print(f"Status: {report['status']}")
    print(f"Linhas: {report['input']['rows']}")
    print(f"SHA-256: {report['input']['sha256']}")
    print(
        "Universos completos: "
        f"fornecedor-ano={report['observed_contract']['supplier_year_rows_complete']} "
        f"UG-ano={report['observed_contract']['ug_year_rows_complete']}"
    )
    print(f"Relatório: {output}")

    if report["status"] == "FAIL":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
