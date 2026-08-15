from __future__ import annotations

import csv
import hashlib
import re
from pathlib import Path

import pandas as pd

from cpgf.version import GEO_VERSION

SIAFI_VERSION = "2025"
SIAFI_SHA256 = "ee2064fb5e0ce5e729365e1a1f2d80f92a55a659da8160cddd10db7f438c0634"

UFS_BRASIL = (
    "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS", "MG",
    "PR", "PB", "PA", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC", "SE", "SP", "TO",
)
UF_DOMINIO_SIAFI = frozenset((*UFS_BRASIL, "EX"))

MANUAL_COMPLEMENTS = {
    "511328": ("SP", "Gerência-Executiva São Paulo - Norte (GEXSPN)"),
    "511341": ("SP", "GERENCIA EXECUTIVA SAO PAULO-LESTE"),
    "510356": ("ES", "UNID.TEC.DE REAB.PROFISSIONAL VITORIA"),
    "110703": ("DF", "SUBSECRETARIA DE PLANEJAMENTO E GESTAO"),
    "110745": ("DF", "SECRETARIA ESPECIAL DE AQUICULTURA E PESCA/PR"),
}

_UF_REGEX = "|".join(UF_DOMINIO_SIAFI)
_PAT_UG_UF = re.compile(
    r'^"(?P<UG>\d{1,6})",.*?,"(?P<UF>' + _UF_REGEX + r')","(?P<COD_ORGAO>\d{1,5})",'
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _best_effort_title(line: str) -> str | None:
    try:
        row = next(csv.reader([line]))
    except (csv.Error, StopIteration):
        return None
    if len(row) < 2:
        return None
    value = row[1].strip()
    return value or None


def load_siafi_ug_dimension(
    path: Path,
    *,
    require_frozen_source: bool = True,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Porta o parser robusto do Geo 1.1.0 para o cadastro SIAFI 2025."""
    path = Path(path)
    if require_frozen_source:
        actual_sha = sha256_file(path)
        if actual_sha != SIAFI_SHA256:
            raise ValueError(
                "Cadastro SIAFI divergente do Geo 1.1.0 congelado: "
                f"esperado={SIAFI_SHA256}; obtido={actual_sha}."
            )

    records: list[dict[str, object]] = []
    failures: list[dict[str, object]] = []
    with path.open("r", encoding="utf-8-sig") as handle:
        next(handle, None)
        for line_number, line in enumerate(handle, start=2):
            match = _PAT_UG_UF.search(line)
            if match is None:
                failures.append({"LINHA": line_number, "TRECHO": line[:250]})
                continue
            records.append(
                {
                    "UG_ID": match.group("UG").zfill(6),
                    "UF_UG": match.group("UF"),
                    "CODIGO_ORGAO_SIAFI": match.group("COD_ORGAO").zfill(5),
                    "TITULO_UG_SIAFI": _best_effort_title(line),
                    "FONTE_UF": "SIAFI_DADOS_UG_2025",
                    "TIPO_FONTE_UF": "CADASTRO_SIAFI",
                    "VERSAO_FONTE_UF": SIAFI_VERSION,
                    "LINHA_ORIGEM_SIAFI": line_number,
                }
            )

    dimension = pd.DataFrame.from_records(records)
    failed = pd.DataFrame.from_records(failures, columns=["LINHA", "TRECHO"])
    if not failed.empty:
        raise ValueError(f"Parser geográfico não cobriu {len(failed)} linhas do SIAFI.")
    if len(dimension) != 49_547 or dimension["UG_ID"].nunique() != 49_547:
        raise ValueError(
            "Cardinalidade do SIAFI divergente do Geo 1.1.0: "
            f"linhas={len(dimension)}, UGs={dimension['UG_ID'].nunique()}."
        )
    if dimension["UG_ID"].duplicated().any():
        raise ValueError("Cadastro SIAFI contém UG duplicada.")
    if not dimension["UG_ID"].str.fullmatch(r"\d{6}").all():
        raise ValueError("Cadastro SIAFI contém UG fora do formato canônico de seis dígitos.")
    if not set(dimension["UF_UG"].dropna().unique()).issubset(UF_DOMINIO_SIAFI):
        raise ValueError("Cadastro SIAFI contém UF fora do domínio congelado.")
    return dimension, failed


def build_ug_geographic_dimension(
    path: Path,
    *,
    require_frozen_source: bool = True,
) -> pd.DataFrame:
    """Constrói a dimensão UG→UF congelada no Geo 1.1.0, com proveniência explícita."""
    siafi, _ = load_siafi_ug_dimension(path, require_frozen_source=require_frozen_source)
    manual = pd.DataFrame.from_records(
        [
            {
                "UG_ID": ug,
                "UF_UG": uf,
                "CODIGO_ORGAO_SIAFI": None,
                "TITULO_UG_SIAFI": title,
                "FONTE_UF": "COMPLEMENTO_MANUAL_2026_08_13",
                "TIPO_FONTE_UF": "COMPLEMENTO_MANUAL",
                "VERSAO_FONTE_UF": "2026-08-13",
                "LINHA_ORIGEM_SIAFI": pd.NA,
            }
            for ug, (uf, title) in MANUAL_COMPLEMENTS.items()
        ]
    )
    overlap = set(siafi["UG_ID"]) & set(manual["UG_ID"])
    if overlap:
        raise ValueError(f"Complemento manual colide com cadastro SIAFI: {sorted(overlap)}")

    dimension = pd.concat([siafi, manual], ignore_index=True)
    if len(dimension) != 49_552 or dimension["UG_ID"].nunique() != 49_552:
        raise ValueError("Dimensão final divergiu das 49.552 UGs congeladas no Geo 1.1.0.")
    return dimension.sort_values("UG_ID", kind="stable").reset_index(drop=True)


def validate_cpgf_geographic_coverage(
    staged: pd.DataFrame,
    dimension: pd.DataFrame,
) -> dict[str, object]:
    """Valida a cobertura Geo 1.1.0 no universo de UGs do snapshot CPGF."""
    cpgf_ugs = set(staged["UG_ID"].dropna().astype("string"))
    siafi_ugs = set(
        dimension.loc[
            dimension["TIPO_FONTE_UF"].eq("CADASTRO_SIAFI"), "UG_ID"
        ].astype("string")
    )
    final_ugs = set(dimension["UG_ID"].astype("string"))
    direct = len(cpgf_ugs & siafi_ugs)
    final = len(cpgf_ugs & final_ugs)
    missing = sorted(cpgf_ugs - final_ugs)

    if len(cpgf_ugs) != 2_153 or direct != 2_148 or final != 2_153 or missing:
        raise ValueError(
            "Cobertura geográfica divergiu da baseline congelada: "
            f"cpgf={len(cpgf_ugs)}, diretas={direct}, finais={final}, faltantes={missing[:10]}."
        )

    matched = staged["UG_ID"].isin(final_ugs)
    record_coverage = float(matched.mean() * 100) if len(staged) else 0.0
    if record_coverage != 100.0:
        raise ValueError(f"Cobertura geográfica dos registros não é 100%: {record_coverage}.")
    return {
        "geo_version": GEO_VERSION,
        "dimension_rows": int(len(dimension)),
        "cpgf_distinct_ugs": len(cpgf_ugs),
        "direct_matches": direct,
        "manual_complements": len(MANUAL_COMPLEMENTS),
        "final_matches": final,
        "coverage_ug_pct": 100.0,
        "coverage_records_pct": record_coverage,
        "siafi_sha256": SIAFI_SHA256,
    }
