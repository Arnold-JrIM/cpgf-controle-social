import yaml
from cpgf.settings.paths import CONFIG_DIR

def test_ai_sql_is_read_only_contract():
    g=yaml.safe_load((CONFIG_DIR/"ai.yaml").read_text(encoding="utf-8"))["ai"]["sql_guardrail"]
    assert g["read_only"] is True and g["allowed_statement"]=="SELECT"
    assert g["allow_ddl"] is False and g["allow_dml"] is False
