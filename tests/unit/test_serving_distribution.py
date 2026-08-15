from __future__ import annotations

import hashlib
import io
import tarfile
from pathlib import Path

import httpx
import pandas as pd
import pytest

from cpgf.dashboard.data import load_dashboard_data
from cpgf.serving import persist_serving_tables
from cpgf.serving.distribution import (
    ServingDistributionConfig,
    ServingUnavailableError,
    bootstrap_serving,
)


def _sample_tables() -> dict[str, pd.DataFrame]:
    return {
        "matrix_supplier_year": pd.DataFrame(
            {
                "CODIGO_UG": ["000001", "000002"],
                "ANO": [2024, 2025],
                "T01": [1, 0],
            }
        ),
        "overlap_supplier_trails": pd.DataFrame(
            {
                "TRILHA_A": ["T01"],
                "TRILHA_B": ["T02"],
                "JACCARD": [0.25],
            }
        ),
    }


def _archive_bundle(bundle_dir: Path, archive_path: Path) -> bytes:
    with tarfile.open(archive_path, "w:gz") as archive:
        for item in sorted(bundle_dir.rglob("*")):
            archive.add(item, arcname=item.relative_to(bundle_dir))
    return archive_path.read_bytes()


def _mock_client(archive: bytes, checksum: str) -> httpx.Client:
    def handler(request: httpx.Request) -> httpx.Response:
        if str(request.url).endswith(".sha256"):
            return httpx.Response(200, text=f"{checksum}  cpgf-serving.tar.gz\n")
        return httpx.Response(200, content=archive)

    return httpx.Client(
        transport=httpx.MockTransport(handler),
        follow_redirects=True,
    )


def test_bootstrap_reuses_valid_local_bundle_without_network(tmp_path):
    bundle = tmp_path / "serving"
    persist_serving_tables(_sample_tables(), bundle)
    config = ServingDistributionConfig(
        bundle_dir=bundle,
        cache_dir=tmp_path / "cache",
        source_url="https://example.test/bundle.tar.gz",
        checksum_url="https://example.test/bundle.tar.gz.sha256",
        offline=True,
    )

    result = bootstrap_serving(config)

    assert result.status == "LOCAL_VALID"
    assert result.validation["status"] == "PASS"
    assert result.catalog_path.is_file()


def test_bootstrap_downloads_checks_hash_extracts_and_validates(tmp_path):
    source = tmp_path / "source"
    persist_serving_tables(_sample_tables(), source)
    archive_bytes = _archive_bundle(source, tmp_path / "bundle.tar.gz")
    checksum = hashlib.sha256(archive_bytes).hexdigest()
    target = tmp_path / "target"
    config = ServingDistributionConfig(
        bundle_dir=target,
        cache_dir=tmp_path / "cache",
        source_url="https://example.test/bundle.tar.gz",
        checksum_url="https://example.test/bundle.tar.gz.sha256",
    )

    with _mock_client(archive_bytes, checksum) as client:
        result = bootstrap_serving(config, client=client)

    assert result.status == "DOWNLOADED_VALID"
    assert result.validation["status"] == "PASS"
    assert (target / "serving_manifest.json").is_file()
    assert (target / "cpgf_serving.duckdb").is_file()


def test_bootstrap_rejects_checksum_mismatch(tmp_path):
    source = tmp_path / "source"
    persist_serving_tables(_sample_tables(), source)
    archive_bytes = _archive_bundle(source, tmp_path / "bundle.tar.gz")
    config = ServingDistributionConfig(
        bundle_dir=tmp_path / "target",
        cache_dir=tmp_path / "cache",
        source_url="https://example.test/bundle.tar.gz",
        checksum_url="https://example.test/bundle.tar.gz.sha256",
    )

    with _mock_client(archive_bytes, "0" * 64) as client:
        with pytest.raises(ServingUnavailableError, match="SHA-256"):
            bootstrap_serving(config, client=client)


def test_bootstrap_rejects_path_traversal_in_archive(tmp_path):
    archive_path = tmp_path / "unsafe.tar.gz"
    payload = b"nao deveria sair do diretorio"
    with tarfile.open(archive_path, "w:gz") as archive:
        info = tarfile.TarInfo("../escape.txt")
        info.size = len(payload)
        archive.addfile(info, io.BytesIO(payload))
    archive_bytes = archive_path.read_bytes()
    checksum = hashlib.sha256(archive_bytes).hexdigest()
    config = ServingDistributionConfig(
        bundle_dir=tmp_path / "target",
        cache_dir=tmp_path / "cache",
        source_url="https://example.test/bundle.tar.gz",
        checksum_url="https://example.test/bundle.tar.gz.sha256",
    )

    with _mock_client(archive_bytes, checksum) as client:
        with pytest.raises(ServingUnavailableError, match="caminho inseguro"):
            bootstrap_serving(config, client=client)

    assert not (tmp_path / "escape.txt").exists()


def test_offline_mode_fails_cleanly_when_bundle_is_missing(tmp_path):
    config = ServingDistributionConfig(
        bundle_dir=tmp_path / "missing",
        cache_dir=tmp_path / "cache",
        source_url="https://example.test/bundle.tar.gz",
        checksum_url="https://example.test/bundle.tar.gz.sha256",
        offline=True,
    )

    with pytest.raises(ServingUnavailableError, match="OFFLINE"):
        bootstrap_serving(config)


def test_dashboard_reads_materialized_bundle_without_recomputing_motor(
    tmp_path, monkeypatch
):
    bundle = tmp_path / "serving"
    persist_serving_tables(_sample_tables(), bundle)

    def fail_recompute(*args, **kwargs):
        raise AssertionError("O dashboard não deve recomputar o motor.")

    monkeypatch.setattr(
        "cpgf.serving.materialize.build_serving_bundle",
        fail_recompute,
    )

    context = load_dashboard_data(bundle_dir=bundle, offline=True)

    assert context.bootstrap.status == "LOCAL_VALID"
    assert context.repository.count("matrix_supplier_year") == 2
    frame = context.repository.read("matrix_supplier_year", limit=1)
    assert len(frame) == 1
