from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

COMPRA_NACIONAL = "COMPRA A/V - R$ - APRES"
COMPRA_INTERNACIONAL = "COMPRA A/V - INT$ - APRES"
COMPRA_PARCELADA = "CPP LOJISTA TRF P/FATURA - REAL"

SAQUES_EFETIVOS = {
    "SAQUE CASH/ATM BB",
    "SAQUE - INT$ - APRES",
    "SAQUE MANUAL - CARTOES BB NA AGENCIA",
    "SAQUE - R$ - APRES",
}

AJUSTES_CONTESTACAO = {
    "COMP A/V-SOL DISP C/CLI-R$ ANT VENC",
    "COMP A/V-SOL DISP C/CLI-R$ APOS VENC",
    "SAQUE BB B24HORAS-SOL C/CLIENTE",
    "VOUCHER - R$ - REVRS REAPR",
}

USECOLS = [
    "CÓDIGO UNIDADE GESTORA",
    "CPF PORTADOR",
    "NOME PORTADOR",
    "CNPJ OU CPF FAVORECIDO",
    "NOME FAVORECIDO",
    "TRANSAÇÃO",
    "DATA TRANSAÇÃO",
    "VALOR TRANSAÇÃO",
]


@dataclass(frozen=True)
class TrailComparison:
    baseline: int
    candidate: int

    @property
    def delta(self) -> int:
        return self.candidate - self.baseline


def sha256_file(path: Path, chunk_size: int = 8 * 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalize_digits(series: pd.Series) -> pd.Series:
    return series.str.replace(r"[^0-9]", "", regex=True).replace("", pd.NA)


def normalize_name(series: pd.Series) -> pd.Series:
    normalized = series.str.strip().str.replace(r"\s+", " ", regex=True).str.upper()
    return normalized.str.normalize("NFKD").str.encode("ascii", "ignore").str.decode("ascii")


def parse_amount(series: pd.Series) -> pd.Series:
    values = series.str.strip().str.replace("R$", "", regex=False).str.replace(" ", "", regex=False)
    contains_comma = values.str.contains(",", regex=False)
    parsed = values.copy()
    parsed.loc[contains_comma] = (
        parsed.loc[contains_comma].str.replace(".", "", regex=False).str.replace(",", ".", regex=False)
    )
    return pd.to_numeric(parsed, errors="coerce")


def load_gate_frame(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(
        path,
        sep=";",
        encoding="utf-8-sig",
        usecols=USECOLS,
        dtype=str,
        keep_default_na=False,
    )

    frame["UG_ID"] = frame["CÓDIGO UNIDADE GESTORA"].str.strip()
    cpf_raw = frame["CPF PORTADOR"].str.strip()
    name_raw = frame["NOME PORTADOR"]
    cpf_digits = normalize_digits(cpf_raw)
    name_normalized = normalize_name(name_raw)
    sigilo_portador = name_raw.str.lower().str.contains("sigilo", na=False)

    frame["PORTADOR_BASELINE"] = cpf_digits.mask(cpf_raw.isin(["", "-1"]) | sigilo_portador)
    frame["NOME_PORTADOR_NORMALIZADO"] = name_normalized
    frame["PORTADOR_CANDIDATO"] = (
        frame["UG_ID"].fillna("")
        + "|"
        + frame["PORTADOR_BASELINE"].fillna("")
        + "|"
        + frame["NOME_PORTADOR_NORMALIZADO"].fillna("")
    ).mask(frame["PORTADOR_BASELINE"].isna())

    favorecido_raw = frame["CNPJ OU CPF FAVORECIDO"].str.strip()
    favorecido_nome = frame["NOME FAVORECIDO"]
    favorecido_digits = normalize_digits(favorecido_raw)
    favorecido_invalido = (
        favorecido_raw.isin(["", "-1"])
        | favorecido_nome.str.lower().str.contains("sigilo", na=False)
        | favorecido_nome.str.lower().str.contains("sem inform", na=False)
    )
    frame["FAVORECIDO_ID"] = favorecido_digits.mask(favorecido_invalido)
    frame["FAVORECIDO_IDENTIFICADO"] = frame["FAVORECIDO_ID"].notna()

    transacao = frame["TRANSAÇÃO"]
    frame["EH_COMPRA_EFETIVA"] = transacao.isin(
        [COMPRA_NACIONAL, COMPRA_INTERNACIONAL, COMPRA_PARCELADA]
    )
    frame["EH_COMPRA_NACIONAL"] = transacao.eq(COMPRA_NACIONAL)
    frame["EH_SAQUE_EFETIVO"] = transacao.isin(SAQUES_EFETIVOS)
    frame["EH_AJUSTE_CONTESTACAO"] = transacao.isin(AJUSTES_CONTESTACAO)
    frame["EH_SIGILOSO"] = (
        frame["TRANSAÇÃO"].str.lower().str.contains("sigilo", na=False)
        | frame["NOME PORTADOR"].str.lower().str.contains("sigilo", na=False)
        | frame["NOME FAVORECIDO"].str.lower().str.contains("sigilo", na=False)
    )

    frame["DATA_DT"] = pd.to_datetime(
        frame["DATA TRANSAÇÃO"].replace("", pd.NA),
        format="%d/%m/%Y",
        errors="coerce",
    )
    frame["ANO_TRANSACAO"] = frame["DATA_DT"].dt.year.astype("Int64")
    frame["VALOR_NUM"] = parse_amount(frame["VALOR TRANSAÇÃO"])
    frame["VALOR_CENTAVOS"] = (frame["VALOR_NUM"] * 100).round().astype("Int64")
    return frame


def identity_universe(frame: pd.DataFrame) -> dict[str, int]:
    identified = frame.loc[frame["PORTADOR_BASELINE"].notna()].copy()
    by_cpf = identified.groupby("PORTADOR_BASELINE", sort=False).agg(
        n_names=("NOME_PORTADOR_NORMALIZADO", "nunique"),
        n_ugs=("UG_ID", "nunique"),
    )
    by_ug_cpf = identified.groupby(["UG_ID", "PORTADOR_BASELINE"], sort=False).agg(
        n_names=("NOME_PORTADOR_NORMALIZADO", "nunique")
    )
    baseline_ug_portador = (
        identified["UG_ID"].astype(str) + "|" + identified["PORTADOR_BASELINE"].astype(str)
    )
    return {
        "portadores_baseline_distintos_global": int(identified["PORTADOR_BASELINE"].nunique()),
        "portadores_baseline_distintos_ug": int(baseline_ug_portador.nunique()),
        "portadores_candidatos_distintos": int(identified["PORTADOR_CANDIDATO"].nunique()),
        "cpf_mascarados_com_multiplos_nomes": int((by_cpf["n_names"] > 1).sum()),
        "cpf_mascarados_presentes_em_multiplas_ugs": int((by_cpf["n_ugs"] > 1).sum()),
        "pares_ug_cpf_com_multiplos_nomes": int((by_ug_cpf["n_names"] > 1).sum()),
    }


def collision_pairs(frame: pd.DataFrame) -> pd.DataFrame:
    identified = frame.loc[frame["PORTADOR_BASELINE"].notna()].copy()
    collisions = (
        identified.groupby(["UG_ID", "PORTADOR_BASELINE"], sort=False)
        .agg(
            n_names=("NOME_PORTADOR_NORMALIZADO", "nunique"),
            n_rows=("PORTADOR_BASELINE", "size"),
        )
        .reset_index()
    )
    return collisions.loc[collisions["n_names"] > 1].copy()


def _t03_groups(frame: pd.DataFrame, portador_col: str) -> pd.DataFrame:
    mask = (
        frame["EH_COMPRA_EFETIVA"]
        & ~frame["EH_AJUSTE_CONTESTACAO"]
        & (frame["VALOR_CENTAVOS"] > 0)
        & frame["DATA_DT"].notna()
        & frame["UG_ID"].ne("")
        & frame[portador_col].notna()
        & frame["FAVORECIDO_IDENTIFICADO"]
    )
    columns = [
        "UG_ID",
        portador_col,
        "FAVORECIDO_ID",
        "DATA_DT",
        "TRANSAÇÃO",
        "VALOR_NUM",
        "VALOR_CENTAVOS",
    ]
    groups = frame.loc[mask, columns].groupby(columns, dropna=False, sort=False).size()
    return groups.loc[groups >= 2].rename("N_TRANSACOES").reset_index()


def compare_t03(frame: pd.DataFrame) -> TrailComparison:
    baseline = _t03_groups(frame, "PORTADOR_BASELINE")
    candidate = _t03_groups(frame, "PORTADOR_CANDIDATO")
    return TrailComparison(len(baseline), len(candidate))


def _t04_groups(frame: pd.DataFrame, portador_col: str) -> pd.DataFrame:
    mask = (
        frame["EH_COMPRA_EFETIVA"]
        & ~frame["EH_AJUSTE_CONTESTACAO"]
        & (frame["VALOR_CENTAVOS"] > 0)
        & frame["DATA_DT"].notna()
        & frame["UG_ID"].ne("")
        & frame[portador_col].notna()
        & frame["FAVORECIDO_IDENTIFICADO"]
    )
    grouped = (
        frame.loc[
            mask,
            ["UG_ID", "FAVORECIDO_ID", "DATA_DT", "VALOR_NUM", "VALOR_CENTAVOS", portador_col],
        ]
        .groupby(
            ["UG_ID", "FAVORECIDO_ID", "DATA_DT", "VALOR_NUM", "VALOR_CENTAVOS"],
            dropna=False,
            sort=False,
        )
        .agg(N_TRANSACOES=(portador_col, "size"), N_PORTADORES=(portador_col, "nunique"))
        .reset_index()
    )
    return grouped.loc[(grouped["N_TRANSACOES"] >= 2) & (grouped["N_PORTADORES"] >= 2)]


def compare_t04(frame: pd.DataFrame) -> TrailComparison:
    baseline = _t04_groups(frame, "PORTADOR_BASELINE")
    candidate = _t04_groups(frame, "PORTADOR_CANDIDATO")
    return TrailComparison(len(baseline), len(candidate))


def _t07(frame: pd.DataFrame, portador_col: str) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    mask = (
        frame["EH_SAQUE_EFETIVO"]
        & frame["DATA_DT"].notna()
        & frame["UG_ID"].ne("")
        & frame[portador_col].notna()
        & frame["VALOR_CENTAVOS"].notna()
    )
    daily = (
        frame.loc[mask, ["UG_ID", portador_col, "DATA_DT", "VALOR_CENTAVOS"]]
        .groupby(["UG_ID", portador_col, "DATA_DT"], dropna=False, sort=False)
        .agg(
            N_SAQUES=(portador_col, "size"),
            TOTAL_CENTAVOS=("VALOR_CENTAVOS", "sum"),
            MAIOR_SAQUE_CENTAVOS=("VALOR_CENTAVOS", "max"),
        )
        .reset_index()
    )
    daily = daily.loc[daily["N_SAQUES"] >= 2].copy()
    daily["ANO_TRANSACAO"] = daily["DATA_DT"].dt.year.astype(int)

    annual = (
        daily.groupby(["UG_ID", portador_col, "ANO_TRANSACAO"], sort=False)
        .agg(
            N_DIAS_MULTISAQUE=("DATA_DT", "size"),
            N_SAQUES_EM_EPISODIOS=("N_SAQUES", "sum"),
            VALOR_EPISODIOS_CENTAVOS=("TOTAL_CENTAVOS", "sum"),
            MAX_SAQUES_DIA=("N_SAQUES", "max"),
        )
        .reset_index()
    )
    limits = (
        annual.groupby("ANO_TRANSACAO")["N_DIAS_MULTISAQUE"]
        .agg(
            N_PORTADORES_COMPARAVEIS_ANO="size",
            LIMIAR_PRIORIZACAO_DIAS=lambda values: values.quantile(0.90, interpolation="linear"),
        )
        .reset_index()
    )
    annual = annual.merge(limits, on="ANO_TRANSACAO", how="left")
    annual["PRIORITARIO"] = (
        (annual["N_DIAS_MULTISAQUE"] >= 3)
        & (annual["N_PORTADORES_COMPARAVEIS_ANO"] >= 10)
        & (annual["N_DIAS_MULTISAQUE"] >= annual["LIMIAR_PRIORIZACAO_DIAS"])
    )
    return daily, annual, annual.loc[annual["PRIORITARIO"]].copy()


def compare_t07(frame: pd.DataFrame) -> dict[str, int]:
    daily_baseline, annual_baseline, priority_baseline = _t07(frame, "PORTADOR_BASELINE")
    daily_candidate, annual_candidate, priority_candidate = _t07(frame, "PORTADOR_CANDIDATO")
    return {
        "episodios_diarios_baseline": len(daily_baseline),
        "episodios_diarios_candidato": len(daily_candidate),
        "portador_anos_recorrencia_baseline": len(annual_baseline),
        "portador_anos_recorrencia_candidato": len(annual_candidate),
        "prioritarios_baseline": len(priority_baseline),
        "prioritarios_candidato": len(priority_candidate),
    }


def t03_sigilo_check(frame: pd.DataFrame) -> dict[str, int]:
    eligible = (
        frame["EH_COMPRA_EFETIVA"]
        & ~frame["EH_AJUSTE_CONTESTACAO"]
        & (frame["VALOR_CENTAVOS"] > 0)
        & frame["DATA_DT"].notna()
        & frame["UG_ID"].ne("")
        & frame["PORTADOR_BASELINE"].notna()
        & frame["FAVORECIDO_IDENTIFICADO"]
    )
    signal_groups = _t03_groups(frame, "PORTADOR_BASELINE")
    join_columns = [
        "UG_ID",
        "PORTADOR_BASELINE",
        "FAVORECIDO_ID",
        "DATA_DT",
        "TRANSAÇÃO",
        "VALOR_CENTAVOS",
    ]
    involved = frame.merge(signal_groups[join_columns], on=join_columns, how="inner")
    return {
        "registros_elegiveis_t03a": int(eligible.sum()),
        "registros_sigilosos_entre_elegiveis_t03a": int((eligible & frame["EH_SIGILOSO"]).sum()),
        "registros_envolvidos_sinais_t03a": len(involved),
        "registros_sigilosos_entre_sinais_t03a": int(involved["EH_SIGILOSO"].sum()),
    }


def _t05_group_candidates(
    group: pd.DataFrame,
    portador_col: str,
    janela_dias: int = 30,
    min_transacoes: int = 5,
    min_portadores: int = 2,
    cv_limite: float = 0.20,
    tolerancia_mediana: float = 0.20,
) -> list[dict[str, object]]:
    if len(group) < 3 or group[portador_col].nunique(dropna=True) < 2:
        return []

    ordered = group.sort_values("DATA_DT").copy()
    dates = ordered["DATA_DT"].to_numpy(dtype="datetime64[D]")
    values = ordered["VALOR_CENTAVOS"].astype("int64").to_numpy()
    portadores = ordered[portador_col].astype(str).to_numpy()
    output: list[dict[str, object]] = []

    for start in np.unique(dates):
        end_limit = start + np.timedelta64(janela_dias, "D")
        in_window = (dates >= start) & (dates <= end_limit)
        window_values = values[in_window]
        window_portadores = portadores[in_window]
        window_dates = dates[in_window]
        n_transactions = len(window_values)
        n_portadores = len(np.unique(window_portadores))
        if n_transactions < min_transacoes or n_portadores < min_portadores:
            continue

        mean = float(window_values.mean())
        std = float(window_values.std(ddof=0))
        cv = std / mean if mean else np.nan
        if not cv <= cv_limite:
            continue

        median = float(np.quantile(window_values, 0.50, method="linear"))
        share = float(
            (
                (window_values >= median * (1 - tolerancia_mediana))
                & (window_values <= median * (1 + tolerancia_mediana))
            ).mean()
        )
        output.append(
            {
                "UG_ID": str(ordered["UG_ID"].iloc[0]),
                "FAVORECIDO_ID": str(ordered["FAVORECIDO_ID"].iloc[0]),
                "ANO_TRANSACAO": int(ordered["ANO_TRANSACAO"].iloc[0]),
                "DT_INICIO": pd.Timestamp(start),
                "DT_FIM": pd.Timestamp(window_dates.max()),
                "N_TRANSACOES": n_transactions,
                "N_PORTADORES": n_portadores,
                "CV": cv,
                "SHARE_DENTRO_FAIXA_MEDIANA": share,
                "VALOR_TOTAL_CENTAVOS": int(window_values.sum()),
            }
        )
    return output


def _deduplicate_t05(candidates: list[dict[str, object]]) -> list[dict[str, object]]:
    if not candidates:
        return []
    ordered = pd.DataFrame(candidates).sort_values(
        ["DT_INICIO", "DT_FIM", "N_TRANSACOES"], ascending=[True, True, False]
    )
    selected: list[dict[str, object]] = []
    cluster: list[dict[str, object]] = []
    cluster_end = None

    def choose(rows: list[dict[str, object]]) -> dict[str, object]:
        options = pd.DataFrame(rows).sort_values(
            ["N_TRANSACOES", "N_PORTADORES", "CV", "VALOR_TOTAL_CENTAVOS", "DT_INICIO"],
            ascending=[False, False, True, False, True],
        )
        return options.iloc[0].to_dict()

    for _, row in ordered.iterrows():
        row_dict = row.to_dict()
        if not cluster:
            cluster = [row_dict]
            cluster_end = row["DT_FIM"]
            continue
        if row["DT_INICIO"] <= cluster_end:
            cluster.append(row_dict)
            cluster_end = max(cluster_end, row["DT_FIM"])
        else:
            selected.append(choose(cluster))
            cluster = [row_dict]
            cluster_end = row["DT_FIM"]
    selected.append(choose(cluster))
    return selected


def compare_t05_affected(frame: pd.DataFrame, baseline_total: int = 1693) -> dict[str, int]:
    collisions = collision_pairs(frame)
    collision_keys = set(
        zip(
            collisions["UG_ID"].astype(str),
            collisions["PORTADOR_BASELINE"].astype(str),
            strict=False,
        )
    )
    row_keys = pd.Series(
        list(
            zip(
                frame["UG_ID"].astype(str),
                frame["PORTADOR_BASELINE"].astype(str),
                strict=False,
            )
        ),
        index=frame.index,
    )
    affected_rows = row_keys.isin(collision_keys)
    affected_group_keys = frame.loc[
        affected_rows
        & frame["EH_COMPRA_NACIONAL"]
        & (frame["VALOR_CENTAVOS"] > 0)
        & frame["DATA_DT"].notna()
        & frame["FAVORECIDO_IDENTIFICADO"]
        & frame["PORTADOR_BASELINE"].notna(),
        ["UG_ID", "FAVORECIDO_ID", "ANO_TRANSACAO"],
    ].drop_duplicates()
    key_set = set(map(tuple, affected_group_keys.astype(str).itertuples(index=False, name=None)))

    national = frame.loc[
        frame["EH_COMPRA_NACIONAL"]
        & (frame["VALOR_CENTAVOS"] > 0)
        & frame["DATA_DT"].notna()
        & frame["FAVORECIDO_IDENTIFICADO"]
        & frame["PORTADOR_BASELINE"].notna(),
        [
            "UG_ID",
            "FAVORECIDO_ID",
            "ANO_TRANSACAO",
            "DATA_DT",
            "VALOR_CENTAVOS",
            "PORTADOR_BASELINE",
            "PORTADOR_CANDIDATO",
        ],
    ].copy()
    national["_KEY"] = list(
        zip(
            national["UG_ID"].astype(str),
            national["FAVORECIDO_ID"].astype(str),
            national["ANO_TRANSACAO"].astype(int).astype(str),
            strict=False,
        )
    )
    national = national.loc[national["_KEY"].isin(key_set)].drop(columns="_KEY")

    def calculate(portador_col: str) -> list[dict[str, object]]:
        episodes: list[dict[str, object]] = []
        for _, group in national.groupby(["UG_ID", "FAVORECIDO_ID", "ANO_TRANSACAO"], sort=False):
            candidates = _t05_group_candidates(group, portador_col)
            episodes.extend(_deduplicate_t05(candidates))
        return episodes

    baseline_affected = calculate("PORTADOR_BASELINE")
    candidate_affected = calculate("PORTADOR_CANDIDATO")
    delta = len(candidate_affected) - len(baseline_affected)
    return {
        "grupos_fornecedor_ano_afetados": len(affected_group_keys),
        "episodios_afetados_baseline": len(baseline_affected),
        "episodios_afetados_candidato": len(candidate_affected),
        "baseline_total": baseline_total,
        "candidato_total_projetado": baseline_total + delta,
    }
