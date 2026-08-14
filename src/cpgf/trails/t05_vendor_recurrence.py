from __future__ import annotations

import numpy as np
import pandas as pd

from .base import ensure_transaction_ids, keyed_signal_id_sha256, require_columns

T05_WINDOW_DAYS = 30
T05_MIN_TRANSACTIONS = 5
T05_MIN_CARDHOLDERS = 2
T05_CV_BASE = 0.20
T05_CV_REINFORCED = 0.10
T05_MEDIAN_TOLERANCE = 0.20
T05_HIGH_ROBUST_SIMILARITY_SHARE = 0.80


def _eligible_t05(staged: pd.DataFrame, portador_column: str) -> pd.DataFrame:
    require_columns(
        staged,
        [
            "UG_ID",
            portador_column,
            "FAVORECIDO_ID",
            "FAVORECIDO_IDENTIFICADO",
            "DATA_DT",
            "ANO_TRANSACAO",
            "VALOR_NUM",
            "VALOR_CENTAVOS",
            "EH_COMPRA_NACIONAL",
        ],
    )
    mask = (
        staged["EH_COMPRA_NACIONAL"].fillna(False)
        & staged["VALOR_CENTAVOS"].gt(0).fillna(False)
        & staged["DATA_DT"].notna()
        & staged["ANO_TRANSACAO"].notna()
        & staged["UG_ID"].notna()
        & staged[portador_column].notna()
        & staged["FAVORECIDO_IDENTIFICADO"].fillna(False)
    )
    eligible = staged.loc[mask].copy()
    portador_key = eligible[portador_column].astype("string")
    drop_columns = {portador_column}
    if "PORTADOR_ID" in eligible.columns:
        drop_columns.add("PORTADOR_ID")
    eligible = eligible.drop(columns=list(drop_columns), errors="ignore")
    eligible["_PORTADOR_T05"] = portador_key
    eligible["ID_TRANSACAO"] = ensure_transaction_ids(staged).loc[eligible.index]
    return eligible


def compute_t05_candidate_windows(
    staged: pd.DataFrame,
    *,
    portador_column: str = "PORTADOR_ID",
) -> pd.DataFrame:
    """Calcula janelas de 30 dias que satisfazem a regra-base congelada de T05.

    A janela é inclusiva entre ``DT_INICIO`` e ``DT_INICIO + 30 dias``, como no
    SQL congelado. Cada data com compra é uma âncora; as métricas robustas são
    calculadas apenas para janelas que já satisfazem N, portadores e CV.
    """
    eligible = _eligible_t05(staged, portador_column)
    ordered = eligible.sort_values(
        ["UG_ID", "FAVORECIDO_ID", "ANO_TRANSACAO", "DATA_DT"],
        kind="mergesort",
    )
    rows: list[dict[str, object]] = []

    grouped = ordered.groupby(
        ["UG_ID", "FAVORECIDO_ID", "ANO_TRANSACAO"],
        sort=False,
        dropna=False,
    )
    for (ug_id, favorecido_id, year), group in grouped:
        if len(group) < T05_MIN_TRANSACTIONS:
            continue
        if group["_PORTADOR_T05"].nunique() < T05_MIN_CARDHOLDERS:
            continue

        dates = group["DATA_DT"].to_numpy(dtype="datetime64[ns]")
        values = group["VALOR_CENTAVOS"].astype("float64").to_numpy()
        cardholders = group["_PORTADOR_T05"].astype(str).to_numpy()

        for start in pd.unique(dates):
            start64 = np.datetime64(start, "ns")
            left = int(np.searchsorted(dates, start64, side="left"))
            limit = start64 + np.timedelta64(T05_WINDOW_DAYS, "D")
            right = int(np.searchsorted(dates, limit, side="right"))
            n_transactions = right - left
            if n_transactions < T05_MIN_TRANSACTIONS:
                continue

            window_cardholders = cardholders[left:right]
            n_cardholders = len(set(window_cardholders.tolist()))
            if n_cardholders < T05_MIN_CARDHOLDERS:
                continue

            window_values = values[left:right]
            mean = float(window_values.mean())
            std = float(window_values.std(ddof=0))
            cv = std / mean if mean else np.nan
            if not np.isfinite(cv) or cv > T05_CV_BASE:
                continue

            median = float(np.median(window_values))
            q1, q3 = (float(value) for value in np.quantile(window_values, [0.25, 0.75]))
            lower = median * (1 - T05_MEDIAN_TOLERANCE)
            upper = median * (1 + T05_MEDIAN_TOLERANCE)
            share_robust = float(((window_values >= lower) & (window_values <= upper)).mean())

            rows.append(
                {
                    "JANELA_DIAS": T05_WINDOW_DAYS,
                    "UG_ID": ug_id,
                    "FAVORECIDO_ID": favorecido_id,
                    "ANO_TRANSACAO": int(year),
                    "DT_INICIO": pd.Timestamp(start64),
                    "DT_FIM": pd.Timestamp(dates[right - 1]),
                    "N_TRANSACOES": n_transactions,
                    "N_PORTADORES": n_cardholders,
                    "MEDIA_CENTAVOS": mean,
                    "DP_CENTAVOS": std,
                    "CV": cv,
                    "MEDIANA_CENTAVOS": median,
                    "Q1_CENTAVOS": q1,
                    "Q3_CENTAVOS": q3,
                    "IQR_CENTAVOS": q3 - q1,
                    "SHARE_DENTRO_FAIXA_MEDIANA": share_robust,
                    "MIN_CENTAVOS": int(window_values.min()),
                    "MAX_CENTAVOS": int(window_values.max()),
                    "VALOR_TOTAL_CENTAVOS": int(window_values.sum()),
                }
            )

    return pd.DataFrame(rows)


def _choose_strongest_window(cluster_rows: list[dict[str, object]]) -> dict[str, object]:
    cluster = pd.DataFrame(cluster_rows).sort_values(
        ["N_TRANSACOES", "N_PORTADORES", "CV", "VALOR_TOTAL_CENTAVOS", "DT_INICIO"],
        ascending=[False, False, True, False, True],
        kind="mergesort",
    )
    return cluster.iloc[0].to_dict()


def deduplicate_t05_episodes(candidates: pd.DataFrame) -> pd.DataFrame:
    """Deduplica janelas sobrepostas sem fundi-las em um período artificial."""
    if candidates.empty:
        return candidates.copy()

    frame = candidates.copy()
    frame["DT_INICIO"] = pd.to_datetime(frame["DT_INICIO"])
    frame["DT_FIM"] = pd.to_datetime(frame["DT_FIM"])
    chosen: list[dict[str, object]] = []

    grouped = frame.groupby(
        ["UG_ID", "FAVORECIDO_ID", "ANO_TRANSACAO"],
        sort=False,
        dropna=False,
    )
    for _, group in grouped:
        ordered = group.sort_values(
            ["DT_INICIO", "DT_FIM", "N_TRANSACOES"],
            ascending=[True, True, False],
            kind="mergesort",
        ).reset_index(drop=True)
        cluster: list[dict[str, object]] = []
        cluster_end: pd.Timestamp | None = None

        for _, row in ordered.iterrows():
            row_dict = row.to_dict()
            if not cluster:
                cluster = [row_dict]
                cluster_end = pd.Timestamp(row["DT_FIM"])
                continue

            if pd.Timestamp(row["DT_INICIO"]) <= cluster_end:
                cluster.append(row_dict)
                cluster_end = max(cluster_end, pd.Timestamp(row["DT_FIM"]))
            else:
                chosen.append(_choose_strongest_window(cluster))
                cluster = [row_dict]
                cluster_end = pd.Timestamp(row["DT_FIM"])

        if cluster:
            chosen.append(_choose_strongest_window(cluster))

    episodes = pd.DataFrame(chosen)
    if episodes.empty:
        return episodes
    return episodes.sort_values(
        ["UG_ID", "FAVORECIDO_ID", "ANO_TRANSACAO", "DT_INICIO"],
        kind="mergesort",
    ).reset_index(drop=True)


def enrich_t05_episodes(episodes: pd.DataFrame) -> pd.DataFrame:
    """Adiciona triagem e atributos interpretáveis sem compor score opaco."""
    if episodes.empty:
        return episodes.copy()

    output = episodes.copy()
    output["NIVEL_TRIAGEM"] = np.where(
        output["CV"].le(T05_CV_REINFORCED), "REFORCADO", "ATENCAO"
    )
    output["PERCENTIL_MATERIALIDADE_ANO"] = output.groupby("ANO_TRANSACAO")[
        "VALOR_TOTAL_CENTAVOS"
    ].rank(pct=True, method="average")
    output["PERCENTIL_RECORRENCIA_ANO"] = output.groupby("ANO_TRANSACAO")[
        "N_TRANSACOES"
    ].rank(pct=True, method="average")
    output["FAIXA_MATERIALIDADE"] = np.select(
        [
            output["PERCENTIL_MATERIALIDADE_ANO"].ge(0.90),
            output["PERCENTIL_MATERIALIDADE_ANO"].ge(0.75),
        ],
        ["ELEVADA", "MODERADA"],
        default="BAIXA",
    )
    output["SIMILARIDADE_ROBUSTA_ALTA"] = output["SHARE_DENTRO_FAIXA_MEDIANA"].ge(
        T05_HIGH_ROBUST_SIMILARITY_SHARE
    )

    def signal_id(row: pd.Series) -> str:
        return keyed_signal_id_sha256(
            "T05",
            row["UG_ID"],
            row["FAVORECIDO_ID"],
            int(row["ANO_TRANSACAO"]),
            pd.Timestamp(row["DT_INICIO"]).date(),
            pd.Timestamp(row["DT_FIM"]).date(),
            int(row["N_TRANSACOES"]),
            round(float(row["CV"]), 8),
            length=24,
        )

    output["ID_SINAL"] = output.apply(signal_id, axis=1)
    first = ["ID_SINAL"]
    return output[first + [column for column in output.columns if column not in first]]


def detect_vendor_recurrence_episodes(
    staged: pd.DataFrame,
    *,
    portador_column: str = "PORTADOR_ID",
) -> pd.DataFrame:
    candidates = compute_t05_candidate_windows(staged, portador_column=portador_column)
    return enrich_t05_episodes(deduplicate_t05_episodes(candidates))


def link_vendor_recurrence_transactions(
    staged: pd.DataFrame,
    episodes: pd.DataFrame,
    *,
    portador_column: str = "PORTADOR_ID",
) -> pd.DataFrame:
    """Cria ponte T05 ↔ compras nacionais contidas no episódio selecionado."""
    if episodes.empty:
        return pd.DataFrame(
            columns=[
                "ID_SINAL",
                "ID_TRANSACAO",
                "UG_ID",
                "FAVORECIDO_ID",
                "PORTADOR_ID",
                "DATA_DT",
                "VALOR_NUM",
                "VALOR_CENTAVOS",
                "COMPETENCIA_ARQUIVO",
                "ARQUIVO_ORIGEM",
            ]
        )

    eligible = _eligible_t05(staged, portador_column).rename(
        columns={"_PORTADOR_T05": "PORTADOR_ID"}
    )
    grouped = {
        key: group
        for key, group in eligible.groupby(
            ["UG_ID", "FAVORECIDO_ID", "ANO_TRANSACAO"],
            sort=False,
            dropna=False,
        )
    }
    pieces: list[pd.DataFrame] = []
    for _, episode in episodes.iterrows():
        key = (episode["UG_ID"], episode["FAVORECIDO_ID"], episode["ANO_TRANSACAO"])
        group = grouped.get(key)
        if group is None:
            continue
        mask = group["DATA_DT"].between(episode["DT_INICIO"], episode["DT_FIM"], inclusive="both")
        selected = group.loc[mask].copy()
        selected.insert(0, "ID_SINAL", episode["ID_SINAL"])
        pieces.append(selected)

    if not pieces:
        return pd.DataFrame()
    bridge = pd.concat(pieces, ignore_index=True)
    columns = [
        "ID_SINAL",
        "ID_TRANSACAO",
        "UG_ID",
        "FAVORECIDO_ID",
        "PORTADOR_ID",
        "DATA_DT",
        "VALOR_NUM",
        "VALOR_CENTAVOS",
    ]
    for optional in ("COMPETENCIA_ARQUIVO", "ARQUIVO_ORIGEM"):
        if optional in bridge.columns:
            columns.append(optional)
    return bridge[columns].reset_index(drop=True)


def run_t05(staged: pd.DataFrame) -> dict[str, pd.DataFrame]:
    candidates = compute_t05_candidate_windows(staged)
    episodes = enrich_t05_episodes(deduplicate_t05_episodes(candidates))
    return {
        "candidates": candidates,
        "episodes": episodes,
        "transactions": link_vendor_recurrence_transactions(staged, episodes),
    }
