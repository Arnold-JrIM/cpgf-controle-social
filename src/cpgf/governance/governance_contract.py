from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from pathlib import Path


def canonical_mapping_sha256(value: Mapping[str, object]) -> str:
    """Calcula SHA-256 determinístico de um contrato JSON já normalizado."""
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def validate_governance_bootstrap_report(
    report: Mapping[str, object],
    contract_path: Path,
) -> dict[str, object]:
    """Converte uma recomputação bootstrap aprovada em gate contra contrato congelado."""
    contract_path = Path(contract_path)
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    expected_digest = str(contract["expected_observed_contract_sha256"])

    observed = report.get("observed_contract")
    if not isinstance(observed, Mapping):
        raise TypeError("Relatório de governança sem observed_contract válido.")

    actual_digest = canonical_mapping_sha256(observed)
    bootstrap_pass = report.get("status") == "BOOTSTRAP_PASS"
    digest_pass = actual_digest == expected_digest
    status = "PASS" if bootstrap_pass and digest_pass else "FAIL"

    return {
        "status": status,
        "bootstrap_pass": bootstrap_pass,
        "expected_observed_contract_sha256": expected_digest,
        "actual_observed_contract_sha256": actual_digest,
        "digest_pass": digest_pass,
        "contract_path": str(contract_path),
    }
