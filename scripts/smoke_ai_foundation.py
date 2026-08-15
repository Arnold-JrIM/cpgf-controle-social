from __future__ import annotations

from pathlib import Path

from streamlit.testing.v1 import AppTest

from cpgf.ai import ToolName, ToolRequest, execute_tool, prepare_assistant_state
from cpgf.ai.guardrails import FreeSQLDisabledError, reject_free_sql
from cpgf.dashboard.data import load_dashboard_data

REPO_ROOT = Path(__file__).resolve().parents[1]
ASSISTANT_PAGE = REPO_ROOT / "pages/07_Assistente_IA.py"


def main() -> None:
    context = load_dashboard_data(offline=True)

    overview = execute_tool(
        context,
        ToolRequest(
            tool=ToolName.OVERVIEW,
            arguments={"year_start": 2025, "year_end": 2025},
        ),
    )
    assert overview.summary["ugs"] > 0
    assert overview.provenance.read_only

    trails = execute_tool(
        context,
        ToolRequest(
            tool=ToolName.TRAIL_PREVALENCE,
            arguments={"year_start": 2025, "year_end": 2025},
        ),
    )
    assert len(trails.records) == 9

    territorial = execute_tool(
        context,
        ToolRequest(
            tool=ToolName.TERRITORIAL_METRIC,
            arguments={
                "reference": "TRANSACAO",
                "year": 2025,
                "metric": "VALOR_TRANSACIONADO_OBSERVAVEL",
            },
        ),
    )
    assert territorial.summary["ufs"] == 27

    state = prepare_assistant_state("Quais estados concentraram maior valor em 2025?")
    assert state.llm_called is False

    try:
        reject_free_sql("SELECT * FROM v_matrix_ug_year")
    except FreeSQLDisabledError:
        pass
    else:
        raise AssertionError("SQL livre deveria estar bloqueado.")

    app = AppTest.from_file(str(ASSISTANT_PAGE), default_timeout=45).run(timeout=45)
    if len(app.exception):
        details = "; ".join(str(item.value) for item in app.exception)
        raise RuntimeError(f"Falha na página Assistente IA: {details}")

    print("AI FOUNDATION SMOKE: PASS")
    print(f"Serving source: {context.bootstrap.status}")
    print(f"UGs 2025: {overview.summary['ugs']}")
    print(f"UFs territorial: {territorial.summary['ufs']}")
    print("Assistant page: PASS")


if __name__ == "__main__":
    main()
