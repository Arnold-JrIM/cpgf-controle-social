from __future__ import annotations

from cpgf.ai import ToolName, ToolRequest, execute_tool, prepare_assistant_state
from cpgf.ai.guardrails import FreeSQLDisabledError, reject_free_sql
from cpgf.dashboard.data import load_dashboard_data


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

    print("AI FOUNDATION SMOKE: PASS")
    print(f"Serving source: {context.bootstrap.status}")
    print(f"UGs 2025: {overview.summary['ugs']}")
    print(f"UFs territorial: {territorial.summary['ufs']}")


if __name__ == "__main__":
    main()
