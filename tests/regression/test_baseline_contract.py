import yaml

from cpgf.settings.paths import CONFIG_DIR


def test_expected_trail_counts_are_frozen():
    config = yaml.safe_load((CONFIG_DIR / "trails.yaml").read_text(encoding="utf-8"))

    assert config["baseline_regression"]["expected_counts"] == {
        "T01": 49675,
        "T02": 14,
        "T03": 7534,
        "T04": 1384,
        "T05": 1693,
        "T06": 233,
        "T07": 1089,
        "T08": 12,
        "T09": 46941,
    }
