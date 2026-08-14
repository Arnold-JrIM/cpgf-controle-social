import yaml

from cpgf.settings.paths import CONFIG_DIR


def test_ai_sql_is_read_only_contract():
    config = yaml.safe_load((CONFIG_DIR / "ai.yaml").read_text(encoding="utf-8"))
    guardrail = config["ai"]["sql_guardrail"]

    assert guardrail["read_only"] is True
    assert guardrail["allowed_statement"] == "SELECT"
    assert guardrail["allow_ddl"] is False
    assert guardrail["allow_dml"] is False
