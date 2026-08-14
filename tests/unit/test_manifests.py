import json
from cpgf.settings.paths import MANIFEST_DIR

def test_baseline_manifest():
    d=json.loads((MANIFEST_DIR/"cpgf.json").read_text(encoding="utf-8"))
    assert d["records"]==1_876_087
    assert d["competencies"]==163
    assert d["competence_start"]=="201301" and d["competence_end"]=="202607"
