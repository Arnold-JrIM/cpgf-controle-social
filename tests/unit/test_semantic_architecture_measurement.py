from __future__ import annotations

import json
from pathlib import Path

MEASUREMENT = Path("data/manifests/semantic_architecture_experiment_measurement_1_0_1.json")


def test_semantic_architecture_measurement_is_frozen() -> None:
    measurement = json.loads(MEASUREMENT.read_text(encoding="utf-8"))

    assert measurement["version"] == "1.0.1"
    assert measurement["status"] == "MEASURED_ON_KNOWN_JH4"
    assert measurement["official_run"]["run_id"] == 31981818344
    assert measurement["official_run"]["head_sha"] == (
        "78cb64a4f0ded0e1e429d2990ef67cc55fee4fab"
    )
    assert measurement["official_run"]["artifact_id"] == 9272652427
    assert measurement["official_run"]["result_json_sha256"] == (
        "eab4001e46707e208dd76527f175d2a796e306bd10c8a79aba6c86b89f6e11a1"
    )
    assert measurement["protocol"]["model"] == "gpt-4o-mini-2024-07-18"
    assert measurement["protocol"]["known_material"] is True

    a = measurement["aggregate"]["A_deterministic"]
    b = measurement["aggregate"]["B_llm_route"]
    c = measurement["aggregate"]["C_hybrid_adjudicated"]
    assert a["mean_joint_exact_rate"] == 0.375
    assert b["mean_joint_exact_rate"] == 0.548611111111111
    assert c["mean_joint_exact_rate"] == 0.4166666666666667
    assert b["mean_route_exact_rate"] == 0.8819444444444444
    assert c["mean_route_exact_rate"] == 0.923611111111111
    assert b["schema_violations"] == 0
    assert c["schema_violations"] == 0

    assert measurement["stability"]["B_llm_route"]["mean_modal_share"] == (
        0.9861111111111112
    )
    assert measurement["stability"]["C_hybrid_adjudicated"]["mean_modal_share"] == (
        0.8680555555555556
    )
    assert measurement["selection"]["B_llm_route"]["eligible"] is True
    assert measurement["selection"]["C_hybrid_adjudicated"]["eligible"] is False
    assert measurement["selection"]["selected_for_future_jh5_candidate"] == "B_llm_route"
    assert measurement["selection"]["selection_is_not_generalization_evidence"] is True

    assert measurement["usage"]["llm_calls_total"] == 288
    assert measurement["usage"]["input_tokens_total"] == 97092
    assert measurement["usage"]["output_tokens_total"] == 12372
    assert measurement["governance"]["production_activation"] is False
    assert measurement["governance"]["retriever_called"] is False
    assert measurement["governance"]["no_prompt_or_architecture_tuning_in_measurement_freeze"] is True
