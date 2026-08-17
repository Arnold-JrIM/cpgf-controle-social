from __future__ import annotations

from cpgf.ai.evidence_contracts import (
    EvidenceBundle,
    EvidenceItem,
    EvidenceNeed,
    EvidencePlan,
    EvidenceSource,
)
from cpgf.ai.grounded_answer import (
    ANSWER_PIPELINE_VERSION,
    ANSWER_POLICY_VERSION,
    AnswerCallMetadata,
    AnswerStatus,
    ClaimVerification,
    OpenAIResponsesAnswerProvider,
    SynthesisCall,
    SynthesisClaim,
    SynthesisDraft,
    VerificationCall,
    VerificationReport,
    VerificationStatus,
    generate_grounded_answer,
)
from cpgf.ai.model_policy import DEFAULT_LLM_MODEL
from cpgf.knowledge.models import (
    AuthorityLevel,
    CorpusScope,
    SourceClass,
    TemporalStatus,
)


def _need(*, required: bool = True) -> EvidenceNeed:
    return EvidenceNeed(
        need_id="need-knowledge",
        source=EvidenceSource.KNOWLEDGE,
        objective="Recuperar evidência documental governada.",
        required=required,
        scopes=(CorpusScope.CPGF_CORE,),
        temporal_statuses=(TemporalStatus.CURRENT,),
        source_classes=(SourceClass.NORMATIVE,),
    )


def _item() -> EvidenceItem:
    return EvidenceItem(
        evidence_id="ev-knowledge-1",
        need_id="need-knowledge",
        source=EvidenceSource.KNOWLEDGE,
        content="A fonte governada registra 15 operações no período analisado.",
        citation="Norma oficial, p. 7",
        source_ref="knowledge://doc-1/chunk-1",
        document_id="doc-1",
        chunk_id="chunk-1",
        page=7,
        source_class=SourceClass.NORMATIVE,
        authority_level=AuthorityLevel.PRIMARY_NORMATIVE,
        scope=CorpusScope.CPGF_CORE,
        temporal_status=TemporalStatus.CURRENT,
        retrieval_method="hybrid",
    )


def _bundle(*, include_item: bool = True, warnings: tuple[str, ...] = ()) -> EvidenceBundle:
    need = _need()
    plan = EvidencePlan(
        question="Quantas operações constam da evidência recuperada?",
        reason="Teste da resposta governada.",
        needs=(need,),
    )
    return EvidenceBundle(
        plan=plan,
        items=(_item(),) if include_item else (),
        warnings=warnings,
    )


def _metadata() -> AnswerCallMetadata:
    return AnswerCallMetadata(
        response_id="resp-test",
        response_model="gpt-4o-mini",
        input_tokens=100,
        output_tokens=20,
        latency_ms=1.0,
    )


class _FakeProvider:
    model = "gpt-4o-mini"

    def __init__(self, draft: SynthesisDraft, report: VerificationReport):
        self.draft = draft
        self.report = report
        self.synthesis_calls = 0
        self.verification_calls = 0

    def synthesize(self, bundle: EvidenceBundle) -> SynthesisCall:
        self.synthesis_calls += 1
        return SynthesisCall(output=self.draft, metadata=_metadata())

    def verify(self, bundle: EvidenceBundle, draft: SynthesisDraft) -> VerificationCall:
        self.verification_calls += 1
        return VerificationCall(output=self.report, metadata=_metadata())


def _claim(
    statement: str = "A evidência registra 15 operações no período analisado.",
    *,
    evidence_ids: tuple[str, ...] = ("ev-knowledge-1",),
) -> SynthesisClaim:
    return SynthesisClaim(
        claim_id="claim-operations",
        statement=statement,
        evidence_ids=evidence_ids,
    )


def _report(status: VerificationStatus = VerificationStatus.SUPPORTED) -> VerificationReport:
    return VerificationReport(
        claim_results=(
            ClaimVerification(
                claim_id="claim-operations",
                status=status,
                checked_evidence_ids=("ev-knowledge-1",),
                reason="A afirmação é diretamente sustentada pelo trecho citado.",
            ),
        )
    )


def test_versions_and_default_model_policy():
    assert ANSWER_PIPELINE_VERSION == "1.0.0"
    assert ANSWER_POLICY_VERSION == "1.0.0"
    provider = OpenAIResponsesAnswerProvider(client=object())
    assert provider.model == DEFAULT_LLM_MODEL == "gpt-4o-mini"


def test_incomplete_bundle_abstains_before_any_llm_call():
    provider = _FakeProvider(SynthesisDraft(claims=(_claim(),)), _report())
    result = generate_grounded_answer(_bundle(include_item=False), provider=provider)

    assert result.answer.status is AnswerStatus.ABSTAINED
    assert result.answer.missing_required_need_ids == ("need-knowledge",)
    assert result.answer.warnings == ("ANSWER_BUNDLE_INCOMPLETE",)
    assert provider.synthesis_calls == 0
    assert provider.verification_calls == 0


def test_simulation_bundle_cannot_ground_user_answer():
    provider = _FakeProvider(SynthesisDraft(claims=(_claim(),)), _report())
    result = generate_grounded_answer(
        _bundle(warnings=("SIMULATION_ONLY: fixture estrutural",)),
        provider=provider,
    )

    assert result.answer.status is AnswerStatus.ABSTAINED
    assert result.answer.warnings == ("ANSWER_SIMULATION_REJECTED",)
    assert provider.synthesis_calls == 0


def test_supported_claim_is_rendered_with_deterministic_citation():
    draft = SynthesisDraft(claims=(_claim(),), limitations=())
    provider = _FakeProvider(draft, _report())

    result = generate_grounded_answer(_bundle(), provider=provider)

    assert result.answer.status is AnswerStatus.ANSWERED
    assert result.answer.supported_claim_ids == ("claim-operations",)
    assert result.answer.rejected_claim_ids == ()
    assert result.answer.text.endswith("[1]")
    assert len(result.answer.citations) == 1
    citation = result.answer.citations[0]
    assert citation.marker == 1
    assert citation.evidence_id == "ev-knowledge-1"
    assert citation.citation == "Norma oficial, p. 7"
    assert provider.synthesis_calls == 1
    assert provider.verification_calls == 1


def test_non_supported_claim_is_not_rendered_as_fact():
    provider = _FakeProvider(
        SynthesisDraft(claims=(_claim(),)),
        _report(VerificationStatus.INSUFFICIENT),
    )

    result = generate_grounded_answer(_bundle(), provider=provider)

    assert result.answer.status is AnswerStatus.ABSTAINED
    assert result.answer.supported_claim_ids == ()
    assert result.answer.rejected_claim_ids == ("claim-operations",)
    assert "15 operações" not in result.answer.text


def test_mixed_report_returns_partial_answer_and_omits_rejected_claim():
    supported = _claim()
    rejected = SynthesisClaim(
        claim_id="claim-extra",
        statement="Há um segundo fato não suficientemente demonstrado.",
        evidence_ids=("ev-knowledge-1",),
    )
    draft = SynthesisDraft(claims=(supported, rejected))
    report = VerificationReport(
        claim_results=(
            ClaimVerification(
                claim_id="claim-operations",
                status=VerificationStatus.SUPPORTED,
                checked_evidence_ids=("ev-knowledge-1",),
                reason="Suportado.",
            ),
            ClaimVerification(
                claim_id="claim-extra",
                status=VerificationStatus.PARTIAL,
                checked_evidence_ids=("ev-knowledge-1",),
                reason="A evidência não cobre toda a afirmação.",
            ),
        )
    )

    result = generate_grounded_answer(_bundle(), provider=_FakeProvider(draft, report))

    assert result.answer.status is AnswerStatus.PARTIAL
    assert result.answer.supported_claim_ids == ("claim-operations",)
    assert result.answer.rejected_claim_ids == ("claim-extra",)
    assert "segundo fato" not in result.answer.text
    assert "omitidas" in result.answer.text


def test_audit_judgment_guard_overrides_even_supported_verdict():
    claim = _claim("A transação comprova fraude no uso do CPGF.")
    provider = _FakeProvider(SynthesisDraft(claims=(claim,)), _report())

    result = generate_grounded_answer(_bundle(), provider=provider)

    assert result.answer.status is AnswerStatus.ABSTAINED
    assert result.answer.human_review_required is True
    assert "fraude" not in result.answer.text.lower()
    assert "AUDIT_JUDGMENT_GUARD:claim-operations" in result.answer.warnings


def test_unknown_evidence_reference_fails_closed_before_verifier():
    provider = _FakeProvider(
        SynthesisDraft(claims=(_claim(evidence_ids=("ev-not-in-bundle",)),)),
        _report(),
    )

    result = generate_grounded_answer(_bundle(), provider=provider)

    assert result.answer.status is AnswerStatus.ABSTAINED
    assert result.answer.warnings == ("ANSWER_SYNTHESIS_FAILED:ValueError",)
    assert provider.synthesis_calls == 1
    assert provider.verification_calls == 0


def test_verifier_must_return_exactly_one_result_for_each_claim():
    provider = _FakeProvider(
        SynthesisDraft(claims=(_claim(),)),
        VerificationReport(claim_results=()),
    )

    result = generate_grounded_answer(_bundle(), provider=provider)

    assert result.answer.status is AnswerStatus.ABSTAINED
    assert result.answer.warnings == ("ANSWER_VERIFICATION_FAILED:ValueError",)
    assert result.report is None


def test_human_review_status_never_becomes_automatic_audit_conclusion():
    provider = _FakeProvider(
        SynthesisDraft(claims=(_claim("A operação demanda revisão humana antes de qualquer conclusão."),)),
        _report(VerificationStatus.HUMAN_REVIEW),
    )

    result = generate_grounded_answer(_bundle(), provider=provider)

    assert result.answer.status is AnswerStatus.ABSTAINED
    assert result.answer.human_review_required is True
    assert result.answer.citations == ()
