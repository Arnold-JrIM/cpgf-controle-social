import hashlib
import json
from pathlib import Path

MANIFEST = Path("data/manifests/retrieval_planner_1_0_0.json")


def _git_blob_sha(path: Path) -> str:
    content = path.read_bytes()
    header = f"blob {len(content)}\0".encode()
    return hashlib.sha1(header + content).hexdigest()


def test_retrieval_planner_manifest_locks_source_before_measurement() -> None:
    payload = json.loads(MANIFEST.read_text(encoding="utf-8"))
    source = Path(payload["planner_source"])

    assert payload["version"] == "1.0.0"
    assert payload["status"] == "FROZEN_BEFORE_MEASUREMENT"
    assert _git_blob_sha(source) == payload["planner_source_git_blob_sha"]
    assert payload["governance"]["planner_rules_must_not_change_after_first_measurement"] is True
    assert payload["governance"]["generalization_claimed"] is False
