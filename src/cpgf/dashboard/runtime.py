from __future__ import annotations

import streamlit as st

from cpgf.dashboard.components import unavailable_state
from cpgf.dashboard.data import DashboardDataContext, load_dashboard_data
from cpgf.serving.distribution import ServingUnavailableError


@st.cache_resource(show_spinner=False)
def get_dashboard_context() -> DashboardDataContext:
    """Mantém o bundle e o catálogo validados entre reruns da sessão Streamlit."""
    return load_dashboard_data()


def require_dashboard_context() -> DashboardDataContext:
    try:
        return get_dashboard_context()
    except ServingUnavailableError as exc:
        unavailable_state(str(exc))
        st.stop()
        raise
