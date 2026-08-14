from __future__ import annotations

import argparse
import json
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

from cpgf.ingestion.cpgf import BLOCKED_STATUS_CODES, create_session, monthly_url
from cpgf.ingestion.kaggle import download_snapshot
from cpgf.ingestion.manifests import load_manifest
from cpgf.ingestion.siafi import discover_latest_csv_resource, download_resource
from cpgf.ingestion.validators import next_competence, validate_siafi_header
from cpgf.settings.paths import MANIFEST_DIR, OUTPUT_DIR

KAGGLE_SIAFI_FILE = "siafi_dados_ug_2025.csv"
RECOGNIZED_PORTAL_STATUSES = {
    "ZIP_AVAILABLE",
    "NOT_AVAILABLE",
    "BLOCKED",
    "HTML_PROTECTION",
}


def probe_cpgf(competence: str, timeout: int = 60) -> dict[str, Any]:
    url = monthly_url(competence)
    session = create_session()

    try:
        with session.get(url, stream=True, timeout=timeout, allow_redirects=True) as response:
            metadata: dict[str, Any] = {
                "competence": competence,
                "url": url,
                "http_status": response.status_code,
                "content_type": response.headers.get("Content-Type"),
                "content_length": response.headers.get("Content-Length"),
            }

            if response.status_code in BLOCKED_STATUS_CODES:
                metadata["status"] = "BLOCKED"
                return metadata
            if response.status_code == 404:
                metadata["status"] = "NOT_AVAILABLE"
                return metadata
            if response.status_code >= 400:
                metadata["status"] = "HTTP_ERROR"
                return metadata

            first_chunk = b""
            for chunk in response.iter_content(chunk_size=4096):
                if chunk:
                    first_chunk = chunk
                    break

            if first_chunk.startswith(b"PK"):
                metadata["status"] = "ZIP_AVAILABLE"
                return metadata

            preview = first_chunk.decode("utf-8", errors="ignore").lower()
            html_markers = ("<html", "<!doctype html", "captcha", "robot", "verifica")
            if any(marker in preview for marker in html_markers):
                metadata["status"] = "HTML_PROTECTION"
                return metadata

            metadata["status"] = "UNEXPECTED_CONTENT"
            metadata["preview_hex"] = first_chunk[:32].hex()
            return metadata
    except requests.RequestException as exc:
        return {
            "competence": competence,
            "url": url,
            "status": "NETWORK_ERROR",
            "error": f"{type(exc).__name__}: {exc}",
        }


def smoke_siafi(temp_dir: Path) -> dict[str, Any]:
    try:
        resource = discover_latest_csv_resource(timeout=60)
        destination = temp_dir / "siafi_official.csv"
        metadata = download_resource(resource, destination, timeout=180)
        return {
            "status": "PASS",
            "resource_id": resource.id,
            "resource_name": resource.name,
            "resource_url": resource.url,
            "last_modified": resource.last_modified,
            "bytes": destination.stat().st_size,
            "schema": metadata["schema"],
            "sha256": metadata["file"]["sha256"],
        }
    except Exception as exc:
        return {
            "status": "FAIL",
            "error": f"{type(exc).__name__}: {exc}",
        }


def _resolve_kaggle_file(resolved: Path, destination: Path, filename: str) -> Path:
    if resolved.is_file():
        return resolved

    direct = resolved / filename
    if direct.exists():
        return direct

    matches = list(destination.rglob(filename))
    if not matches:
        raise FileNotFoundError(f"Arquivo {filename} não encontrado após download do Kaggle.")
    return matches[0]


def smoke_kaggle(temp_dir: Path) -> dict[str, Any]:
    try:
        destination = temp_dir / "kaggle"
        resolved = download_snapshot(destination, path=KAGGLE_SIAFI_FILE)
        candidate = _resolve_kaggle_file(Path(resolved), destination, KAGGLE_SIAFI_FILE)
        schema = validate_siafi_header(candidate)
        if not schema["valid"]:
            raise ValueError(f"Schema Kaggle inválido: {schema['missing_columns']}")
        return {
            "status": "PASS",
            "file": str(candidate),
            "bytes": candidate.stat().st_size,
            "schema": schema,
        }
    except Exception as exc:
        return {
            "status": "FAIL",
            "error": f"{type(exc).__name__}: {exc}",
        }


def evaluate(report: dict[str, Any]) -> tuple[str, list[str]]:
    failures: list[str] = []
    degraded = False

    baseline_status = report["cpgf"]["baseline"]["status"]
    next_status = report["cpgf"]["next_competence"]["status"]

    if baseline_status not in {"ZIP_AVAILABLE", "BLOCKED", "HTML_PROTECTION"}:
        failures.append(f"CPGF baseline retornou {baseline_status}")
    if baseline_status in {"BLOCKED", "HTML_PROTECTION"}:
        degraded = True

    if next_status not in RECOGNIZED_PORTAL_STATUSES:
        failures.append(f"CPGF próxima competência retornou {next_status}")
    if next_status in {"BLOCKED", "HTML_PROTECTION"}:
        degraded = True

    if report["siafi"]["status"] != "PASS":
        failures.append("SIAFI oficial falhou")
    if report["kaggle"]["status"] != "PASS":
        failures.append("Kaggle público falhou")

    if failures:
        return "FAIL", failures
    if degraded:
        return "PASS_WITH_PORTAL_PROTECTION", failures
    return "PASS", failures


def run_smoke(output: Path) -> dict[str, Any]:
    baseline = load_manifest(MANIFEST_DIR / "cpgf.json")
    baseline_competence = str(baseline["competence_end"])
    next_candidate = next_competence(baseline_competence)

    with tempfile.TemporaryDirectory(prefix="cpgf-smoke-") as temp:
        temp_dir = Path(temp)
        report: dict[str, Any] = {
            "executed_at_utc": datetime.now(timezone.utc).isoformat(),
            "baseline_competence": baseline_competence,
            "cpgf": {
                "baseline": probe_cpgf(baseline_competence),
                "next_competence": probe_cpgf(next_candidate),
            },
            "siafi": smoke_siafi(temp_dir),
            "kaggle": smoke_kaggle(temp_dir),
        }

    overall, failures = evaluate(report)
    report["overall_status"] = overall
    report["failures"] = failures

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def print_summary(report: dict[str, Any], output: Path) -> None:
    print("=== Smoke test de ingestão ===")
    print(f"Status geral: {report['overall_status']}")
    print(f"CPGF baseline: {report['cpgf']['baseline']['status']}")
    print(f"CPGF próxima competência: {report['cpgf']['next_competence']['status']}")
    print(f"SIAFI oficial: {report['siafi']['status']}")
    print(f"Kaggle público: {report['kaggle']['status']}")
    print(f"Relatório: {output}")
    for failure in report["failures"]:
        print(f"FALHA: {failure}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Smoke test real das fontes externas de ingestão.")
    parser.add_argument(
        "--output",
        type=Path,
        default=OUTPUT_DIR / "smoke" / "ingestion_smoke.json",
    )
    args = parser.parse_args()

    report = run_smoke(args.output)
    print_summary(report, args.output)
    if report["overall_status"] == "FAIL":
        sys.exit(1)


if __name__ == "__main__":
    main()
