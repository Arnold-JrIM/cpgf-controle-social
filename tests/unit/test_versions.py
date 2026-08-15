from cpgf.version import (
    APP_VERSION,
    GEO_VERSION,
    KNOWLEDGE_VERSION,
    MOTOR_VERSION,
    PREPARATION_BASELINE_VERSION,
    PREPARATION_VERSION,
    RULES_VERSION,
    SERVING_VERSION,
)


def test_methodology_versions():
    assert APP_VERSION == "0.6.0-dev"
    assert PREPARATION_BASELINE_VERSION == "1.0.0"
    assert PREPARATION_VERSION == "1.1.0"
    assert RULES_VERSION == "1.2.0"
    assert MOTOR_VERSION == "1.3.2"
    assert SERVING_VERSION == "1.5.0"
    assert GEO_VERSION == "1.1.0"
    assert KNOWLEDGE_VERSION == "1.1.0"
