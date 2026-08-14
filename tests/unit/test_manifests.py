import json

from cpgf.settings.paths import MANIFEST_DIR


def test_baseline_manifest():
    data = json.loads((MANIFEST_DIR / "cpgf.json").read_text(encoding="utf-8"))

    assert data["records"] == 1_876_087
    assert data["competencies"] == 163
    assert data["competence_start"] == "201301"
    assert data["competence_end"] == "202607"
