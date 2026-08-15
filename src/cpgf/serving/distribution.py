from __future__ import annotations

import hashlib
import os
import shutil
import tarfile
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

from cpgf.settings.paths import SERVING_DIR
from cpgf.version import SERVING_VERSION

from .materialize import validate_serving_bundle

_RELEASE_TAG = f"serving-v{SERVING_VERSION}"
_RELEASE_ASSET = f"cpgf-serving-{SERVING_VERSION}.tar.gz"
DEFAULT_RELEASE_URL = (
    "https://github.com/Arnold-JrIM/cpgf-controle-social/releases/download/"
    f"{_RELEASE_TAG}/{_RELEASE_ASSET}"
)
DEFAULT_CHECKSUM_URL = f"{DEFAULT_RELEASE_URL}.sha256"


class ServingUnavailableError(RuntimeError):
    """Indica que não foi possível disponibilizar um bundle íntegro de serving."""


@dataclass(frozen=True)
class ServingBootstrapResult:
    status: str
    bundle_dir: Path
    catalog_path: Path
    source_url: str | None
    validation: dict[str, Any]


@dataclass(frozen=True)
class ServingDistributionConfig:
    bundle_dir: Path
    cache_dir: Path
    source_url: str
    checksum_url: str
    offline: bool = False

    @classmethod
    def from_env(cls) -> "ServingDistributionConfig":
        bundle_dir = Path(os.getenv("CPGF_SERVING_BUNDLE_DIR", str(SERVING_DIR)))
        cache_dir = Path(
            os.getenv(
                "CPGF_SERVING_CACHE_DIR",
                str(bundle_dir.parent / ".serving-cache"),
            )
        )
        source_url = os.getenv("CPGF_SERVING_BUNDLE_URL", DEFAULT_RELEASE_URL)
        checksum_url = os.getenv(
            "CPGF_SERVING_CHECKSUM_URL",
            f"{source_url}.sha256",
        )
        offline = os.getenv("CPGF_SERVING_OFFLINE", "0").strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }
        return cls(
            bundle_dir=bundle_dir,
            cache_dir=cache_dir,
            source_url=source_url,
            checksum_url=checksum_url,
            offline=offline,
        )


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _parse_checksum(payload: str) -> str:
    token = payload.strip().split()[0] if payload.strip() else ""
    if len(token) != 64 or any(char not in "0123456789abcdefABCDEF" for char in token):
        raise ServingUnavailableError("Checksum remoto inválido para o bundle de serving.")
    return token.lower()


def _download_to_path(
    url: str,
    destination: Path,
    *,
    client: httpx.Client,
) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        with client.stream("GET", url) as response:
            response.raise_for_status()
            with destination.open("wb") as handle:
                for chunk in response.iter_bytes():
                    handle.write(chunk)
    except (httpx.HTTPError, OSError) as exc:
        raise ServingUnavailableError(f"Falha ao baixar o serving de {url}: {exc}") from exc


def _download_text(url: str, *, client: httpx.Client) -> str:
    try:
        response = client.get(url)
        response.raise_for_status()
        return response.text
    except httpx.HTTPError as exc:
        raise ServingUnavailableError(f"Falha ao obter checksum de {url}: {exc}") from exc


def _safe_extract_tar(archive_path: Path, destination: Path) -> None:
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    root = destination.resolve()

    try:
        with tarfile.open(archive_path, mode="r:gz") as archive:
            for member in archive.getmembers():
                if member.issym() or member.islnk():
                    raise ServingUnavailableError(
                        f"Bundle contém link não permitido: {member.name}"
                    )
                if not (member.isfile() or member.isdir()):
                    raise ServingUnavailableError(
                        f"Bundle contém entrada não suportada: {member.name}"
                    )
                target = (root / member.name).resolve()
                if os.path.commonpath([str(root), str(target)]) != str(root):
                    raise ServingUnavailableError(
                        f"Bundle contém caminho inseguro: {member.name}"
                    )
            archive.extractall(root)
    except (tarfile.TarError, OSError) as exc:
        raise ServingUnavailableError(f"Falha ao extrair bundle de serving: {exc}") from exc


def _validated_bundle(bundle_dir: Path) -> dict[str, Any] | None:
    bundle_dir = Path(bundle_dir)
    if not (bundle_dir / "serving_manifest.json").is_file():
        return None
    if not (bundle_dir / "cpgf_serving.duckdb").is_file():
        return None
    try:
        validation = validate_serving_bundle(bundle_dir)
    except Exception:
        return None
    return validation if validation.get("status") == "PASS" else None


def bootstrap_serving(
    config: ServingDistributionConfig | None = None,
    *,
    force_download: bool = False,
    client: httpx.Client | None = None,
) -> ServingBootstrapResult:
    """Disponibiliza um bundle íntegro sem recomputar trilhas ou governança."""
    config = config or ServingDistributionConfig.from_env()
    bundle_dir = Path(config.bundle_dir)

    if not force_download:
        validation = _validated_bundle(bundle_dir)
        if validation is not None:
            return ServingBootstrapResult(
                status="LOCAL_VALID",
                bundle_dir=bundle_dir,
                catalog_path=bundle_dir / "cpgf_serving.duckdb",
                source_url=None,
                validation=validation,
            )

    if config.offline:
        raise ServingUnavailableError(
            "Bundle local ausente ou inválido e CPGF_SERVING_OFFLINE está habilitado."
        )

    owns_client = client is None
    http_client = client or httpx.Client(timeout=120.0, follow_redirects=True)
    config.cache_dir.mkdir(parents=True, exist_ok=True)
    archive_path = config.cache_dir / _RELEASE_ASSET

    try:
        expected_sha = _parse_checksum(
            _download_text(config.checksum_url, client=http_client)
        )
        _download_to_path(config.source_url, archive_path, client=http_client)
        actual_sha = _sha256_file(archive_path)
        if actual_sha != expected_sha:
            raise ServingUnavailableError(
                "SHA-256 do bundle de serving diverge do checksum publicado."
            )

        bundle_dir.parent.mkdir(parents=True, exist_ok=True)
        temp_dir = Path(
            tempfile.mkdtemp(prefix=".serving-bootstrap-", dir=bundle_dir.parent)
        )
        try:
            _safe_extract_tar(archive_path, temp_dir)
            validation = _validated_bundle(temp_dir)
            if validation is None:
                raise ServingUnavailableError(
                    "Bundle baixado falhou na validação interna de integridade."
                )

            if bundle_dir.exists():
                shutil.rmtree(bundle_dir)
            temp_dir.replace(bundle_dir)
        except Exception:
            shutil.rmtree(temp_dir, ignore_errors=True)
            raise

        return ServingBootstrapResult(
            status="DOWNLOADED_VALID",
            bundle_dir=bundle_dir,
            catalog_path=bundle_dir / "cpgf_serving.duckdb",
            source_url=config.source_url,
            validation=validation,
        )
    finally:
        if owns_client:
            http_client.close()
