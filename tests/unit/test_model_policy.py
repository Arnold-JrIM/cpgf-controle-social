import pytest

from cpgf.ai.model_policy import (
    DEFAULT_LLM_MODEL,
    LLM_MODEL_POLICY_VERSION,
    project_llm_model,
    resolve_project_llm_model,
)


def test_project_llm_model_is_fixed_to_gpt_4o_mini():
    assert DEFAULT_LLM_MODEL == "gpt-4o-mini"
    assert project_llm_model() == "gpt-4o-mini"
    assert resolve_project_llm_model() == "gpt-4o-mini"
    assert resolve_project_llm_model("gpt-4o-mini") == "gpt-4o-mini"
    assert LLM_MODEL_POLICY_VERSION == "1.0.0"


def test_model_policy_rejects_any_other_model():
    with pytest.raises(ValueError, match="política exige gpt-4o-mini"):
        resolve_project_llm_model("gpt-4o")
