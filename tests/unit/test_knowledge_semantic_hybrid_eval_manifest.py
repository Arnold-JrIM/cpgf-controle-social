from __future__ import annotations

import json
from pathlib import Path


MANIFEST = Path("data/manifests/knowledge_semantic_hybrid_eval_1_0_0.json")


def test_semantic_hybrid_evaluation_manifest_is_frozen() -> None:
    payload = json.loads(MANIFEST.read_text(encoding="utf-8"))

    assert payload["artifact"] == "knowledge_semantic_hybrid_evaluation"
    assert payload["version"] == "1.0.0"
    assert payload["benchmark_sha256"] == (
        "6633babe7e17f4c0fefb0523ea477a11257bad87d3c0bc258dea7db1c33c1777"
    )
    assert payload["chunks_sha256"] == (
        "43c7d61e8b963c5b8b1ad747ec24c2cdb5e464d403ea9b2b3776f19a5cb65b7c"
    )
    assert payload["local_result_file_sha256"] == (
        "d07c6ef4839718acd74636a9a8ed38917cdce13b49a0eb2fbb75309ec4078a22"
    )
    assert payload["semantic_index"]["local_artifact_sha256"] == (
        "f11396ef4b3d48efa6f5bcfbce574b52064a087cfcd6b485dcba8fec9fdfa351"
    )
    assert payload["validation"]["gold_documents_with_chunks"] == 24
    assert payload["validation"]["missing_gold_documents"] == []

    governed = {
        method: payload["results"][method]["governed"]
        for method in ("lexical", "semantic", "hybrid")
    }
    assert governed["semantic"]["hit_rate_at_5"] == governed["hybrid"]["hit_rate_at_5"]
    assert governed["semantic"]["mean_document_recall_at_5"] > governed["hybrid"][
        "mean_document_recall_at_5"
    ]
    assert governed["semantic"]["map_at_5"] > governed["hybrid"]["map_at_5"]
    assert governed["hybrid"]["mrr"] > governed["semantic"]["mrr"]
    assert governed["semantic"]["failed_case_ids"] == ["KRET-004"]
    assert governed["hybrid"]["failed_case_ids"] == ["KRET-004"]

    governance = payload["governance"]
    assert governance["llm_called"] is False
    assert governance["sql_executed"] is False
    assert governance["full_result_committed"] is False
    assert governance["semantic_index_committed"] is False
