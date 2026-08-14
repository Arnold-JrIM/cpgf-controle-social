from cpgf.settings.loader import load_yaml

def test_load_app_config():
    cfg=load_yaml("app.yaml")
    assert cfg["methodology"]["rules_version"]=="1.2.0"
    assert cfg["methodology"]["motor_governance_version"]=="1.3.2"
    assert cfg["methodology"]["geographic_enrichment_version"]=="1.1.0"
