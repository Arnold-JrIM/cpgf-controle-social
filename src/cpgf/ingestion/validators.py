from __future__ import annotations

import csv
import hashlib
import re
from pathlib import Path
from typing import Iterable

CPGF_REFERENCE_COLUMNS = (
    "CÓDIGO ÓRGÃO SUPERIOR",
    "NOME ÓRGÃO SUPERIOR",
    "CÓDIGO ÓRGÃO",
    "NOME ÓRGÃO",
    "CÓDIGO UNIDADE GESTORA",
    "NOME UNIDADE GESTORA",
    "ANO EXTRATO",
    "MÊS EXTRATO",
    "CPF PORTADOR",
    "NOME PORTADOR",
    "CNPJ OU CPF FAVORECIDO",
    "NOME FAVORECIDO",
    "TRANSAÇÃO",
    "DATA TRANSAÇÃO",
    "VALOR TRANSAÇÃO",
)

ENCODING_CANDIDATES = ("utf-8-sig", "utf-8", "cp1252", "latin1")
DELIMITER_CANDIDATES = (";", ",", "\t")


def validate_competence(competence: str) -> bool:
    return bool(re.fullmatch(r"20\d{2}(0[1-9]|1[0-2])", str(competence)))


def next_competence(competence: str) -> str:
    if not validate_competence(competence):
        raise ValueError(f"Competência inválida: {competence}")
    year = int(competence[:4])
    month = int(competence[4:])
    if month == 12:
        return f"{year + 1}01"
    return f"{year}{month + 1:02d}"


def competence_range(start: str, end: str) -> list[str]:
    if not validate_competence(start) or not validate_competence(end):
        raise ValueError("Competência inicial/final inválida.")
    if start > end:
        raise ValueError("A competência inicial não pode ser maior que a final.")
    result: list[str] = []
    current = start
    while current <= end:
        result.append(current)
        current = next_competence(current)
    return result


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        while chunk := stream.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def has_zip_signature(path: Path) -> bool:
    path = Path(path)
    if not path.exists() or path.stat().st_size < 4:
        return False
    with path.open("rb") as stream:
        return stream.read(4).startswith(b"PK")


def detect_text_encoding(path: Path, sample_bytes: int = 100_000) -> str:
    sample = Path(path).read_bytes()[:sample_bytes]
    for encoding in ENCODING_CANDIDATES:
        try:
            sample.decode(encoding)
            return encoding
        except UnicodeDecodeError:
            continue
    raise UnicodeError(f"Não foi possível detectar a codificação de {path}.")


def detect_delimiter(header_text: str) -> str:
    counts = {delimiter: header_text.count(delimiter) for delimiter in DELIMITER_CANDIDATES}
    delimiter = max(counts, key=counts.get)
    if counts[delimiter] == 0:
        raise ValueError("Separador CSV não identificado no cabeçalho.")
    return delimiter


def read_csv_header(path: Path) -> tuple[str, str, list[str]]:
    encoding = detect_text_encoding(path)
    with Path(path).open("r", encoding=encoding, newline="") as stream:
        first_line = stream.readline()
    delimiter = detect_delimiter(first_line)
    header = next(csv.reader([first_line], delimiter=delimiter))
    return encoding, delimiter, [value.strip() for value in header]


def validate_header_contains(path: Path, required_columns: Iterable[str]) -> dict[str, object]:
    encoding, delimiter, header = read_csv_header(path)
    required = list(required_columns)
    missing = [column for column in required if column not in header]
    return {
        "encoding": encoding,
        "delimiter": delimiter,
        "header": header,
        "missing_columns": missing,
        "valid": not missing,
    }


def validate_cpgf_header(path: Path) -> dict[str, object]:
    result = validate_header_contains(path, CPGF_REFERENCE_COLUMNS)
    result["same_reference_set"] = set(result["header"]) == set(CPGF_REFERENCE_COLUMNS)
    result["same_reference_order"] = result["header"] == list(CPGF_REFERENCE_COLUMNS)
    return result


def validate_siafi_header(path: Path) -> dict[str, object]:
    return validate_header_contains(path, ("UG", "Título", "UF"))
