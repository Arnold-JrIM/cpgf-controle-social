from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from pathlib import Path

EIGENDECOMPOSITION_SIGNATURE_MARKERS: tuple[str, ...] = (
    "_components",
    "_loadings",
    "_condition",
)


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


def portable_governance_contract(observed: Mapping[str, object]) -> dict[str, object]:
    """Normaliza o contrato para comparação reprodutível entre ambientes numéricos.

    Matrizes binárias, sobreposição, marginalidade, elegibilidade e VIF continuam
    congelados por SHA-256 exato. Para saídas diretamente dependentes de
    eigendecomposição, congelam-se nome, cardinalidade e esquema, mas não o hash dos
    valores de autovetores/autovalores. BLAS/LAPACK distintos podem produzir bases
    numericamente equivalentes em subespaços degenerados sem alterar o fenômeno.
    """
    signatures = observed.get("signatures")
    if not isinstance(signatures, Mapping):
        raise TypeError("observed_contract sem mapa de signatures válido.")

    portable: dict[str, object] = {
        key: value for key, value in observed.items() if key != "signatures"
    }
    portable_signatures: dict[str, object] = {}

    for raw_name, raw_signature in signatures.items():
        name = str(raw_name)
        if not isinstance(raw_signature, Mapping):
            raise TypeError(f"Assinatura inválida para {name!r}.")

        if any(marker in name for marker in EIGENDECOMPOSITION_SIGNATURE_MARKERS):
            portable_signatures[name] = {
                "rows": raw_signature.get("rows"),
                "columns": raw_signature.get("columns"),
            }
        else:
            portable_signatures[name] = dict(raw_signature)

    portable["signatures"] = portable_signatures
    return portable


def validate_governance_bootstrap_report(
    report: Mapping[str, object],
    contract_path: Path,
) -> dict[str, object]:
    """Valida uma recomputação integral contra o contrato portátil congelado."""
    contract_path = Path(contract_path)
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    expected_digest = str(
        contract.get(
            "expected_portable_contract_sha256",
            contract.get("expected_observed_contract_sha256", ""),
        )
    )
    if not expected_digest:
        raise ValueError("Manifesto sem digest esperado do contrato de governança.")

    observed = report.get("observed_contract")
    if not isinstance(observed, Mapping):
        raise TypeError("Relatório de governança sem observed_contract válido.")

    portable = portable_governance_contract(observed)
    actual_digest = canonical_mapping_sha256(portable)
    bootstrap_pass = report.get("status") == "BOOTSTRAP_PASS"
    digest_pass = actual_digest == expected_digest
    status = "PASS" if bootstrap_pass and digest_pass else "FAIL"

    return {
        "status": status,
        "bootstrap_pass": bootstrap_pass,
        "contract_mode": "PORTABLE_NUMERICAL",
        "expected_portable_contract_sha256": expected_digest,
        "actual_portable_contract_sha256": actual_digest,
        "digest_pass": digest_pass,
        "contract_path": str(contract_path),
    }
