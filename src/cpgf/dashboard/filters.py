from __future__ import annotations

import streamlit as st

from cpgf.dashboard.components import render_partial_period_note
from cpgf.dashboard.data import DashboardDataContext, DashboardFilter, available_years


def sidebar_filters(
    context: DashboardDataContext,
    *,
    key_prefix: str,
    allow_ug: bool = True,
) -> DashboardFilter:
    years = available_years(context)
    if not years:
        raise ValueError("Serving sem anos disponíveis.")

    st.sidebar.markdown("### Filtros")
    selected = st.sidebar.select_slider(
        "Período",
        options=years,
        value=(years[0], years[-1]),
        key=f"{key_prefix}_years",
    )
    year_start, year_end = int(selected[0]), int(selected[1])

    ug_codes: tuple[str, ...] = ()
    if allow_ug:
        raw = st.sidebar.text_input(
            "Código(s) de UG",
            placeholder="Ex.: 170001, 153163",
            help="Opcional. Separe múltiplos códigos por vírgula.",
            key=f"{key_prefix}_ugs",
        )
        ug_codes = tuple(
            dict.fromkeys(
                item.strip()
                for item in raw.split(",")
                if item.strip()
            )
        )

    st.sidebar.caption(
        "Os filtros atuam sobre as matrizes materializadas. "
        "Nenhuma trilha é recalculada na interface."
    )
    render_partial_period_note(year_end)
    return DashboardFilter(year_start=year_start, year_end=year_end, ug_codes=ug_codes)
