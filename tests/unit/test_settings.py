from cpgf.settings.loader import load_yaml


def test_load_app_config():
    config = load_yaml("app.yaml")

    assert config["methodology"]["rules_version"] == "1.2.0"
    assert config["methodology"]["motor_governance_version"] == "1.3.2"
    assert config["methodology"]["geographic_enrichment_version"] == "1.1.0"
