from cpgf.version import (
    GEO_VERSION,
    MOTOR_VERSION,
    PREPARATION_BASELINE_VERSION,
    PREPARATION_VERSION,
    RULES_VERSION,
    SERVING_VERSION,
)


def test_methodology_versions():
    assert PREPARATION_BASELINE_VERSION == "1.0.0"
    assert PREPARATION_VERSION == "1.1.0"
    assert RULES_VERSION == "1.2.0"
    assert MOTOR_VERSION == "1.3.2"
    assert SERVING_VERSION == "1.4.0"
    assert GEO_VERSION == "1.1.0"
