from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

import pandas as pd

from .exposure import build_supplier_year_universe, build_ug_year_universe

SUPPLIER_CORE_TRAILS: tuple[str, ...] = ("T01", "T02", "T03", "T04", "T05", "T06")
UG_CORE_TRAILS: tuple[str, ...] = ("T01", "T02", "T03", "T04", "T05", "T06", "T07")
CONTEXT_TRAILS: tuple[str, ...] = ("T08", "T09")


@dataclass(frozen=True)
class TrailFlagSpec:
    trail: str
    entity_column: str | None
    year_column: str | None = "ANO_TRANSACAO"
    date_column: str | None = None


TRAIL_FLAG_SPECS: dict[str, TrailFlagSpec] = {
    "T01": TrailFlagSpec("T01", "FAVORECIDO_ID", year_column=None, date_column="DATA_DT"),
    "T02": TrailFlagSpec("T02", "FAVORECIDO_ID", year_column=None, date_column="DATA_DT"),
    "T03": TrailFlagSpec("T03", "FAVORECIDO_ID", year_column=None, date_column="DATA_DT"),
    "T04": TrailFlagSpec("T04", "FAVORECIDO_ID", year_column=None, date_column="DATA_DT"),
    "T05": TrailFlagSpec("T05", "FAVORECIDO_ID"),
    "T06": TrailFlagSpec("T06", "TOP1_FAVORECIDO_ID"),
    "T07": TrailFlagSpec("T07", None),
    "T08": TrailFlagSpec("T08", None),
    "T09": TrailFlagSpec("T09", "FAVORECIDO_ID"),
}

FLAG_LONG_COLUMNS: tuple[str, ...] = (
    "CODIGO_TRILHA",
    "CODIGO_UG",
    "CHAVE_ENTIDADE",
    "ANO",
)


def _require_columns(frame: pd.DataFrame, columns: tuple[str, ...], context: str) -> None:
    missing = [column for column in columns if column not in frame.columns]
    if missing:
        raise ValueError(f"Colunas ausentes em {context}: {missing}")


def _year_series(frame: pd.DataFrame, spec: TrailFlagSpec) -> pd.Series:
    if spec.year_column and spec.year_column in frame.columns:
        return pd.to_numeric(frame[spec.year_column], errors="coerce").astype("Int64")
    if spec.date_column and spec.date_column in frame.columns:
        return pd.to_datetime(frame[spec.date_column], errors="coerce").dt.year.astype("Int64")
    expected = [column for column in (spec.year_column, spec.date_column) if column]
    raise ValueError(f"{spec.trail}: coluna temporal ausente; esperado um de {expected}.")


def build_flag_records(primary_outputs: Mapping[str, pd.DataFrame]) -> pd.DataFrame:
    """Normaliza as saídas primárias T01–T09 para o contrato longo de flags.

    O adaptador não recalcula trilhas. Ele apenas projeta UG, entidade observável e
    ano para as unidades diagnósticas do Motor 1.3.2. T07/T08 não recebem entidade;
    T06 usa o fornecedor Top-1 que originou o sinal estrutural.
    """
    pieces: list[pd.DataFrame] = []
    for raw_code, frame in primary_outputs.items():
        code = str(raw_code).strip().upper()
        if code not in TRAIL_FLAG_SPECS:
            raise ValueError(f"Trilha desconhecida para matriz de flags: {raw_code!r}")
        if frame.empty:
            continue

        spec = TRAIL_FLAG_SPECS[code]
        _require_columns(frame, ("UG_ID",), code)
        if spec.entity_column is not None and spec.entity_column not in frame.columns:
            raise ValueError(f"{code}: coluna de entidade ausente: {spec.entity_column}")

        piece = pd.DataFrame(index=frame.index)
        piece["CODIGO_TRILHA"] = code
        piece["CODIGO_UG"] = frame["UG_ID"].astype("string")
        if spec.entity_column is None:
            piece["CHAVE_ENTIDADE"] = pd.Series(pd.NA, index=frame.index, dtype="string")
        else:
            piece["CHAVE_ENTIDADE"] = frame[spec.entity_column].astype("string")
        piece["ANO"] = _year_series(frame, spec)
        piece = piece.loc[piece["CODIGO_UG"].notna() & piece["ANO"].notna()].copy()
        pieces.append(piece.loc[:, FLAG_LONG_COLUMNS])

    if not pieces:
        return pd.DataFrame(columns=FLAG_LONG_COLUMNS)

    return (
        pd.concat(pieces, ignore_index=True)
        .drop_duplicates()
        .sort_values(["ANO", "CODIGO_UG", "CODIGO_TRILHA", "CHAVE_ENTIDADE"], kind="stable")
        .reset_index(drop=True)
    )


def _pivot_flags(
    flags_long: pd.DataFrame,
    *,
    trails: tuple[str, ...],
    keys: list[str],
) -> pd.DataFrame:
    if flags_long.empty:
        return pd.DataFrame(columns=[*keys, *trails])

    filtered = flags_long.loc[flags_long["CODIGO_TRILHA"].isin(trails)].copy()
    if "CHAVE_ENTIDADE" in keys:
        filtered = filtered.loc[filtered["CHAVE_ENTIDADE"].notna()].copy()
    if filtered.empty:
        return pd.DataFrame(columns=[*keys, *trails])

    pivot = (
        filtered.assign(FLAG=1)
        .pivot_table(
            index=keys,
            columns="CODIGO_TRILHA",
            values="FLAG",
            aggfunc="max",
            fill_value=0,
        )
        .reset_index()
    )
    pivot.columns.name = None
    for trail in trails:
        if trail not in pivot.columns:
            pivot[trail] = 0
    return pivot.loc[:, [*keys, *trails]]


def _add_core_family_flags_supplier(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    result["F1"] = result[["T01", "T02"]].sum(axis=1).gt(0).astype("int8")
    result["F2"] = result[["T03", "T04", "T05"]].sum(axis=1).gt(0).astype("int8")
    result["F3"] = result["T06"].astype("int8")
    result["N_TRILHAS_ATIVAS"] = result[list(SUPPLIER_CORE_TRAILS)].sum(axis=1).astype("Int64")
    result["N_FAMILIAS_ATIVAS"] = result[["F1", "F2", "F3"]].sum(axis=1).astype("Int64")
    return result


def _add_core_family_flags_ug(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    result["F1"] = result[["T01", "T02"]].sum(axis=1).gt(0).astype("int8")
    result["F2"] = result[["T03", "T04", "T05"]].sum(axis=1).gt(0).astype("int8")
    result["F3"] = result["T06"].astype("int8")
    result["F4"] = result["T07"].astype("int8")
    result["N_TRILHAS_NUCLEO"] = result[list(UG_CORE_TRAILS)].sum(axis=1).astype("Int64")
    result["N_FAMILIAS_NUCLEO"] = result[["F1", "F2", "F3", "F4"]].sum(axis=1).astype("Int64")
    return result


def _attach_supplier_contexts(matrix: pd.DataFrame, flags_long: pd.DataFrame) -> pd.DataFrame:
    result = matrix.copy()

    t08 = _pivot_flags(flags_long, trails=("T08",), keys=["CODIGO_UG", "ANO"])
    t08 = t08.rename(columns={"T08": "T08_CONTEXTO"})
    result = result.merge(t08, on=["CODIGO_UG", "ANO"], how="left", validate="many_to_one")

    t09 = _pivot_flags(
        flags_long,
        trails=("T09",),
        keys=["CODIGO_UG", "CHAVE_ENTIDADE", "ANO"],
    ).rename(columns={"T09": "T09_CONTEXTO"})
    result = result.merge(
        t09,
        on=["CODIGO_UG", "CHAVE_ENTIDADE", "ANO"],
        how="left",
        validate="one_to_one",
    )
    for column in ("T08_CONTEXTO", "T09_CONTEXTO"):
        if column not in result.columns:
            result[column] = 0
        result[column] = result[column].fillna(0).astype("int8")
    return result


def _attach_ug_contexts(matrix: pd.DataFrame, flags_long: pd.DataFrame) -> pd.DataFrame:
    result = matrix.copy()
    context = _pivot_flags(flags_long, trails=CONTEXT_TRAILS, keys=["CODIGO_UG", "ANO"])
    context = context.rename(columns={"T08": "T08_CONTEXTO", "T09": "T09_CONTEXTO"})
    result = result.merge(context, on=["CODIGO_UG", "ANO"], how="left", validate="one_to_one")
    for column in ("T08_CONTEXTO", "T09_CONTEXTO"):
        if column not in result.columns:
            result[column] = 0
        result[column] = result[column].fillna(0).astype("int8")
    return result


def build_supplier_year_flag_matrix(
    universe: pd.DataFrame,
    flags_long: pd.DataFrame,
) -> pd.DataFrame:
    """Projeta T01–T06 no universo UG × fornecedor × ano e anexa T08/T09 como contexto."""
    keys = ["CODIGO_UG", "CHAVE_ENTIDADE", "ANO"]
    _require_columns(universe, tuple(keys), "universo fornecedor-ano")
    _require_columns(flags_long, FLAG_LONG_COLUMNS, "flags longas")

    pivot = _pivot_flags(flags_long, trails=SUPPLIER_CORE_TRAILS, keys=keys)
    result = universe.merge(pivot, on=keys, how="left", validate="one_to_one")
    for trail in SUPPLIER_CORE_TRAILS:
        result[trail] = result[trail].fillna(0).astype("int8")
    result = _add_core_family_flags_supplier(result)
    result = _attach_supplier_contexts(result, flags_long)
    return result.reset_index(drop=True)


def build_ug_year_flag_matrix(
    universe: pd.DataFrame,
    flags_long: pd.DataFrame,
) -> pd.DataFrame:
    """Projeta T01–T07 no universo UG × ano e anexa T08/T09 sem somá-los ao núcleo."""
    keys = ["CODIGO_UG", "ANO"]
    _require_columns(universe, tuple(keys), "universo UG-ano")
    _require_columns(flags_long, FLAG_LONG_COLUMNS, "flags longas")

    pivot = _pivot_flags(flags_long, trails=UG_CORE_TRAILS, keys=keys)
    result = universe.merge(pivot, on=keys, how="left", validate="one_to_one")
    for trail in UG_CORE_TRAILS:
        result[trail] = result[trail].fillna(0).astype("int8")
    result = _add_core_family_flags_ug(result)
    result = _attach_ug_contexts(result, flags_long)
    return result.reset_index(drop=True)


def build_diagnostic_matrices(
    staged: pd.DataFrame,
    primary_outputs: Mapping[str, pd.DataFrame],
) -> dict[str, pd.DataFrame]:
    """Constrói os dois universos de exposição e projeta as saídas primárias sobre eles."""
    flags_long = build_flag_records(primary_outputs)
    supplier_universe = build_supplier_year_universe(staged)
    ug_universe = build_ug_year_universe(staged)
    return {
        "flags_long": flags_long,
        "supplier_year": build_supplier_year_flag_matrix(supplier_universe, flags_long),
        "ug_year": build_ug_year_flag_matrix(ug_universe, flags_long),
    }
