from __future__ import annotations

from collections import Counter
from pathlib import Path

from pydantic import BaseModel, ConfigDict, model_validator

from cpgf.benchmark.orchestration_holdout_v2 import (
    OrchestrationHoldoutV2Case,
    OrchestrationHoldoutV2Category,
    load_orchestration_holdout_v2,
)

ORCHESTRATION_HOLDOUT_V2_PATCH_VERSION = "2.0.1"
ORCHESTRATION_HOLDOUT_V2_PATCH_BASE_VERSION = "2.0.0"
CORRECTED_CASE_IDS = ("OH2-017", "OH2-038", "OH2-052", "OH2-053", "OH2-054")


class OrchestrationHoldoutV2PatchSuite(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    version: str = ORCHESTRATION_HOLDOUT_V2_PATCH_VERSION
    cases: tuple[OrchestrationHoldoutV2Case, ...]

    @model_validator(mode="after")
    def validate_suite(self) -> "OrchestrationHoldoutV2PatchSuite":
        if self.version != ORCHESTRATION_HOLDOUT_V2_PATCH_VERSION:
            raise ValueError("Versão inesperada do Orchestration Holdout 2 corrigido")
        if len(self.cases) != 56:
            raise ValueError("Orchestration Holdout 2.0.1 deve conter exatamente 56 casos")
        ids = [case.id for case in self.cases]
        if ids != [f"OH2-{index:03d}" for index in range(1, 57)]:
            raise ValueError("IDs devem formar a sequência OH2-001..OH2-056")
        if len(ids) != len(set(ids)):
            raise ValueError("IDs duplicados no Orchestration Holdout 2.0.1")
        counts = Counter(case.category.value for case in self.cases)
        required = {category.value: 8 for category in OrchestrationHoldoutV2Category}
        if counts != required:
            raise ValueError(f"Categorias desbalanceadas: {dict(counts)}")
        return self


def load_orchestration_holdout_v2_patch(
    path: Path | str,
) -> OrchestrationHoldoutV2PatchSuite:
    base_schema_suite = load_orchestration_holdout_v2(path)
    return OrchestrationHoldoutV2PatchSuite(cases=base_schema_suite.cases)


def validate_question_only_patch(
    original: Path | str,
    corrected: Path | str,
) -> dict[str, object]:
    before = load_orchestration_holdout_v2(original)
    after = load_orchestration_holdout_v2_patch(corrected)

    before_by_id = {case.id: case for case in before.cases}
    after_by_id = {case.id: case for case in after.cases}
    if set(before_by_id) != set(after_by_id):
        raise ValueError("OH2.0.1 alterou o conjunto de IDs")

    changed: list[str] = []
    for case_id in before_by_id:
        old_payload = before_by_id[case_id].model_dump(mode="json")
        new_payload = after_by_id[case_id].model_dump(mode="json")
        old_question = old_payload.pop("question")
        new_question = new_payload.pop("question")
        if old_payload != new_payload:
            raise ValueError(f"{case_id} alterou oracle ou contrato além da pergunta")
        if old_question != new_question:
            changed.append(case_id)

    if tuple(changed) != CORRECTED_CASE_IDS:
        raise ValueError(
            f"OH2.0.1 deve alterar somente {CORRECTED_CASE_IDS}; observado={tuple(changed)}"
        )

    return {
        "status": "PASS",
        "original_version": ORCHESTRATION_HOLDOUT_V2_PATCH_BASE_VERSION,
        "corrected_version": ORCHESTRATION_HOLDOUT_V2_PATCH_VERSION,
        "cases": len(after.cases),
        "changed_case_ids": changed,
        "changed_field": "question",
        "oracles_changed": False,
    }
