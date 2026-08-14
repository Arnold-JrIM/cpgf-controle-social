from __future__ import annotations

import random
import shutil
import time
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests

from .manifests import file_record
from .validators import has_zip_signature, next_competence, validate_competence, validate_cpgf_header

DEFAULT_BASE_URL = "https://portaldatransparencia.gov.br/download-de-dados/cpgf"
BLOCKED_STATUS_CODES = {403, 429}


class CPGFIngestionError(RuntimeError):
    """Erro base da ingestão do CPGF."""


class PortalBlocked(CPGFIngestionError):
    """O Portal sinalizou bloqueio ou proteção antirrobô."""


class PortalReturnedHTML(CPGFIngestionError):
    """O Portal retornou HTML em vez do ZIP esperado."""


class CompetenceNotAvailable(CPGFIngestionError):
    """A competência consultada ainda não está disponível."""


@dataclass(frozen=True)
class DownloadedCompetence:
    competence: str
    csv_path: Path
    source_url: str
    file_metadata: dict[str, Any]
    schema_metadata: dict[str, object]


def monthly_url(competence: str, base_url: str = DEFAULT_BASE_URL) -> str:
    if not validate_competence(competence):
        raise ValueError(f"Competência inválida: {competence}")
    return f"{base_url.rstrip('/')}/{competence}"


def create_session() -> requests.Session:
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": "Mozilla/5.0 (compatible; CPGF-Control-Social/0.1)",
            "Accept": "application/zip,application/octet-stream,*/*;q=0.8",
            "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.7",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
        }
    )
    return session


def _looks_like_html(path: Path) -> bool:
    preview = Path(path).read_bytes()[:4096].decode("utf-8", errors="ignore").lower()
    markers = ("<html", "<!doctype html", "captcha", "robot", "javascript", "verifica")
    return any(marker in preview for marker in markers)


def download_month_zip(
    competence: str,
    destination: Path,
    *,
    session: requests.Session | None = None,
    base_url: str = DEFAULT_BASE_URL,
    timeout: int = 1800,
) -> Path:
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = destination.with_suffix(destination.suffix + ".part")
    partial.unlink(missing_ok=True)
    url = monthly_url(competence, base_url)
    http = session or create_session()

    try:
        with http.get(url, stream=True, timeout=timeout, allow_redirects=True) as response:
            if response.status_code in BLOCKED_STATUS_CODES:
                raise PortalBlocked(f"Portal retornou HTTP {response.status_code} para {competence}.")
            if response.status_code == 404:
                raise CompetenceNotAvailable(f"Competência {competence} não disponível (HTTP 404).")
            response.raise_for_status()
            with partial.open("wb") as stream:
                for chunk in response.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        stream.write(chunk)
    except Exception:
        partial.unlink(missing_ok=True)
        raise

    if not has_zip_signature(partial):
        is_html = _looks_like_html(partial)
        partial.unlink(missing_ok=True)
        if is_html:
            raise PortalReturnedHTML(
                f"Portal retornou conteúdo HTML para {competence}; validação humana pode ser necessária."
            )
        raise CPGFIngestionError(f"Conteúdo recebido para {competence} não é ZIP válido.")

    partial.replace(destination)
    return destination


def select_csv_member(archive: zipfile.ZipFile, competence: str) -> zipfile.ZipInfo:
    members = [
        member
        for member in archive.infolist()
        if not member.is_dir() and member.filename.lower().endswith(".csv")
    ]
    if not members:
        raise CPGFIngestionError("Nenhum CSV encontrado no ZIP do CPGF.")
    if len(members) == 1:
        return members[0]
    matching = [member for member in members if competence in Path(member.filename).name]
    return max(matching or members, key=lambda member: member.file_size)


def extract_month_csv(
    zip_path: Path,
    destination_dir: Path,
    competence: str,
    *,
    delete_zip: bool = True,
) -> Path:
    if not validate_competence(competence):
        raise ValueError(f"Competência inválida: {competence}")
    zip_path = Path(zip_path)
    destination_dir = Path(destination_dir)
    destination_dir.mkdir(parents=True, exist_ok=True)
    destination = destination_dir / f"{competence}_CPGF.csv"
    partial = destination.with_suffix(destination.suffix + ".part")

    if destination.exists() and destination.stat().st_size > 0:
        if delete_zip:
            zip_path.unlink(missing_ok=True)
        return destination
    if not zipfile.is_zipfile(zip_path):
        raise CPGFIngestionError(f"ZIP inválido: {zip_path}")

    partial.unlink(missing_ok=True)
    with zipfile.ZipFile(zip_path) as archive:
        member = select_csv_member(archive, competence)
        with archive.open(member) as source, partial.open("wb") as target:
            shutil.copyfileobj(source, target)
    partial.replace(destination)
    if delete_zip:
        zip_path.unlink(missing_ok=True)
    return destination


def download_and_extract_month(
    competence: str,
    raw_dir: Path,
    *,
    session: requests.Session | None = None,
    temp_dir: Path | None = None,
    base_url: str = DEFAULT_BASE_URL,
    timeout: int = 1800,
) -> DownloadedCompetence:
    raw_dir = Path(raw_dir)
    existing_csv = raw_dir / f"{competence}_CPGF.csv"
    url = monthly_url(competence, base_url)
    if existing_csv.exists() and existing_csv.stat().st_size > 0:
        schema = validate_cpgf_header(existing_csv)
        if not schema["valid"]:
            raise CPGFIngestionError(
                f"CSV existente {competence} não contém as colunas mínimas esperadas: "
                f"{schema['missing_columns']}"
            )
        return DownloadedCompetence(
            competence=competence,
            csv_path=existing_csv,
            source_url=url,
            file_metadata=file_record(
                existing_csv, competence=competence, source_url=url, reused_existing=True
            ),
            schema_metadata=schema,
        )

    temp_dir = Path(temp_dir) if temp_dir else raw_dir / ".tmp"
    temp_dir.mkdir(parents=True, exist_ok=True)
    zip_path = temp_dir / f"{competence}_CPGF.zip"
    download_month_zip(
        competence,
        zip_path,
        session=session,
        base_url=base_url,
        timeout=timeout,
    )
    csv_path = extract_month_csv(zip_path, raw_dir, competence, delete_zip=True)
    schema = validate_cpgf_header(csv_path)
    if not schema["valid"]:
        csv_path.unlink(missing_ok=True)
        raise CPGFIngestionError(
            f"CSV {competence} não contém as colunas mínimas esperadas: {schema['missing_columns']}"
        )

    return DownloadedCompetence(
        competence=competence,
        csv_path=csv_path,
        source_url=url,
        file_metadata=file_record(csv_path, competence=competence, source_url=url),
        schema_metadata=schema,
    )


def update_incremental(
    last_known_competence: str,
    raw_dir: Path,
    *,
    session: requests.Session | None = None,
    max_new_competences: int = 24,
    base_url: str = DEFAULT_BASE_URL,
    min_pause_seconds: float = 25.0,
    max_pause_seconds: float = 45.0,
) -> list[DownloadedCompetence]:
    if not validate_competence(last_known_competence):
        raise ValueError(f"Competência inválida: {last_known_competence}")
    if max_new_competences < 1:
        raise ValueError("max_new_competences deve ser >= 1.")
    if min_pause_seconds < 0 or max_pause_seconds < min_pause_seconds:
        raise ValueError("Intervalo de pausa inválido.")

    results: list[DownloadedCompetence] = []
    competence = next_competence(last_known_competence)
    http = session or create_session()

    for _ in range(max_new_competences):
        try:
            result = download_and_extract_month(
                competence,
                raw_dir,
                session=http,
                base_url=base_url,
            )
        except CompetenceNotAvailable:
            break
        results.append(result)
        competence = next_competence(competence)
        if len(results) < max_new_competences and max_pause_seconds > 0:
            time.sleep(random.uniform(min_pause_seconds, max_pause_seconds))

    return results


def download_range(
    start: str,
    end: str,
    raw_dir: Path,
    *,
    session: requests.Session | None = None,
    base_url: str = DEFAULT_BASE_URL,
    min_pause_seconds: float = 25.0,
    max_pause_seconds: float = 45.0,
) -> list[DownloadedCompetence]:
    from .validators import competence_range

    competencies = competence_range(start, end)
    results: list[DownloadedCompetence] = []
    http = session or create_session()
    for index, competence in enumerate(competencies):
        results.append(
            download_and_extract_month(
                competence,
                raw_dir,
                session=http,
                base_url=base_url,
            )
        )
        if index < len(competencies) - 1 and max_pause_seconds > 0:
            time.sleep(random.uniform(min_pause_seconds, max_pause_seconds))
    return results
