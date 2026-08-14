from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import requests

from .manifests import file_record
from .validators import validate_siafi_header

DEFAULT_CKAN_API_URL = (
    "https://www.tesourotransparente.gov.br/ckan/api/3/action/"
    "package_show?id=siafi-relatorio-unidades-gestoras"
)


class SIAFIIngestionError(RuntimeError):
    """Erro da ingestão do cadastro de Unidades Gestoras do SIAFI."""


@dataclass(frozen=True)
class SIAFIResource:
    id: str
    name: str
    url: str
    format: str
    last_modified: str | None
    created: str | None
    size: int | None


def _timestamp_key(value: str | None) -> datetime:
    if not value:
        return datetime.min
    normalized = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return datetime.min
    return parsed.replace(tzinfo=None) if parsed.tzinfo else parsed


def _resource_from_dict(resource: dict[str, Any]) -> SIAFIResource:
    return SIAFIResource(
        id=str(resource.get("id", "")),
        name=str(resource.get("name", "")),
        url=str(resource.get("url", "")),
        format=str(resource.get("format", "")),
        last_modified=resource.get("last_modified"),
        created=resource.get("created"),
        size=(int(resource["size"]) if str(resource.get("size", "")).isdigit() else None),
    )


def discover_latest_csv_resource(
    *,
    session: requests.Session | None = None,
    api_url: str = DEFAULT_CKAN_API_URL,
    timeout: int = 60,
) -> SIAFIResource:
    http = session or requests.Session()
    response = http.get(api_url, timeout=timeout)
    response.raise_for_status()
    payload = response.json()
    if payload.get("success") is not True or not isinstance(payload.get("result"), dict):
        raise SIAFIIngestionError("Resposta CKAN inválida ou sem result.")

    resources = payload["result"].get("resources", [])
    candidates = []
    for resource in resources:
        fmt = str(resource.get("format", "")).strip().upper()
        url = str(resource.get("url", ""))
        if fmt == "CSV" or url.lower().split("?")[0].endswith(".csv"):
            candidates.append(_resource_from_dict(resource))
    if not candidates:
        raise SIAFIIngestionError("Nenhum recurso CSV encontrado no dataset CKAN do SIAFI.")

    return max(
        candidates,
        key=lambda resource: (
            _timestamp_key(resource.last_modified or resource.created),
            resource.size or 0,
        ),
    )


def download_resource(
    resource: SIAFIResource,
    destination: Path,
    *,
    session: requests.Session | None = None,
    timeout: int = 600,
) -> dict[str, Any]:
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = destination.with_suffix(destination.suffix + ".part")
    partial.unlink(missing_ok=True)
    http = session or requests.Session()

    try:
        with http.get(resource.url, stream=True, timeout=timeout, allow_redirects=True) as response:
            response.raise_for_status()
            with partial.open("wb") as stream:
                for chunk in response.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        stream.write(chunk)
    except Exception:
        partial.unlink(missing_ok=True)
        raise

    partial.replace(destination)
    schema = validate_siafi_header(destination)
    if not schema["valid"]:
        destination.unlink(missing_ok=True)
        raise SIAFIIngestionError(
            f"CSV SIAFI sem colunas mínimas esperadas: {schema['missing_columns']}"
        )

    return {
        "resource": resource.__dict__,
        "file": file_record(destination, source_url=resource.url, resource_id=resource.id),
        "schema": schema,
    }
