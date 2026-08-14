from __future__ import annotations

import io
import zipfile

import pytest
import requests

from cpgf.ingestion.cpgf import (
    CompetenceNotAvailable,
    PortalBlocked,
    PortalReturnedHTML,
    download_month_zip,
    extract_month_csv,
)


class FakeResponse:
    def __init__(self, status_code: int, content: bytes):
        self.status_code = status_code
        self.content = content

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def iter_content(self, chunk_size: int):
        yield self.content

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}")


class FakeSession:
    def __init__(self, response: FakeResponse):
        self.response = response

    def get(self, *args, **kwargs):
        return self.response


def make_zip(csv_name: str = "202607_CPGF.csv", csv_bytes: bytes = b"A;B\n1;2\n") -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(csv_name, csv_bytes)
    return buffer.getvalue()


def test_download_valid_zip(tmp_path):
    destination = tmp_path / "month.zip"
    result = download_month_zip(
        "202607",
        destination,
        session=FakeSession(FakeResponse(200, make_zip())),
    )
    assert result == destination
    assert zipfile.is_zipfile(result)


def test_download_blocked_and_not_available(tmp_path):
    with pytest.raises(PortalBlocked):
        download_month_zip(
            "202607",
            tmp_path / "blocked.zip",
            session=FakeSession(FakeResponse(429, b"blocked")),
        )
    with pytest.raises(CompetenceNotAvailable):
        download_month_zip(
            "202608",
            tmp_path / "missing.zip",
            session=FakeSession(FakeResponse(404, b"not found")),
        )


def test_html_is_rejected(tmp_path):
    with pytest.raises(PortalReturnedHTML):
        download_month_zip(
            "202607",
            tmp_path / "html.zip",
            session=FakeSession(FakeResponse(200, b"<!doctype html><html>captcha</html>")),
        )


def test_extract_preserves_csv_bytes(tmp_path):
    csv_bytes = b"col1;col2\r\nA;B\r\n"
    zip_path = tmp_path / "month.zip"
    zip_path.write_bytes(make_zip(csv_bytes=csv_bytes))
    output = extract_month_csv(zip_path, tmp_path / "raw", "202607", delete_zip=True)
    assert output.read_bytes() == csv_bytes
    assert not zip_path.exists()
