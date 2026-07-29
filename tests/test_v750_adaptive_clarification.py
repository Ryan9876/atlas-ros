from atlas_ros.intent_learning_policy_v750 import (
    AdaptiveClarificationPolicyV750,
    AdaptiveInputProcessingWithClarificationV750,
)
from atlas_ros.intent_learning_v750 import (
    ClarificationDecisionV1,
    ClarificationStatus,
    CompletionDimensionsV1,
    ConsequenceAssessmentV1,
    ContextFamiliarityV1,
    EvidenceLevel,
    IntentEvidenceV1,
    RelatedRecordV1,
    RelationshipClassification,
    decide_relationship,
)


def completion(outcome: str, done: str) -> CompletionDimensionsV1:
    return CompletionDimensionsV1(
        intended_outcome=outcome,
        scope="ANX customer devices",
        definition_of_done=done,
        accountable_owner="Ryan",
        ryan_management_action="approve and track",
        execution_evidence="verified record",
        completion_boundary=done,
    )


def familiar(score: float = 0.9) -> ContextFamiliarityV1:
    return ContextFamiliarityV1(
        user=0.95,
        domain=score,
        project=score,
        terminology=score,
        evidence_recency=score,
        interpretation_consistency=score,
    )


def test_exact_duplicate_requires_completion_equivalence() -> None:
    proposed = completion("standard naming", "approved naming standard")
    decision = decide_relationship(
        capture="Define a standard naming convention for ANX customer devices",
        proposed_completion=proposed,
        related_records=(
            RelatedRecordV1(
                record_id="a1",
                title="Define a standard naming convention for ANX customer devices",
                completion=proposed,
            ),
        ),
        familiarity=familiar(),
        consequence=ConsequenceAssessmentV1(),
    )
    assert decision.relationship is RelationshipClassification.EXACT_DUPLICATE
    assert decision.clarification_status is ClarificationStatus.NOT_REQUIRED
    assert decision.provider_writes == 0


def test_paraphrased_duplicate_requires_all_dimensions() -> None:
    proposed = completion("standard naming", "approved naming standard")
    decision = decide_relationship(
        capture="Create the ANX device naming standard",
        proposed_completion=proposed,
        related_records=(
            RelatedRecordV1(
                record_id="a1",
                title="Define a standard naming convention",
                completion=proposed,
            ),
        ),
        familiarity=familiar(),
        consequence=ConsequenceAssessmentV1(),
    )
    assert decision.relationship is RelationshipClassification.PARAPHRASED_DUPLICATE


def test_anx_central_management_is_preserved_and_clarified() -> None:
    records = (
        RelatedRecordV1(
            record_id="naming",
            title="ANX device naming convention",
            completion=completion("standard naming", "approved naming standard"),
        ),
        RelatedRecordV1(
            record_id="snmp",
            title="Install SNMP discovery probes in LIT and ALL",
            completion=completion(
                "CMDB discovery",
                "customer devices discovered in CMDB",
            ),
        ),
    )
    decision = decide_relationship(
        capture="centrally manage ANX customer devices",
        proposed_completion=None,
        related_records=records,
        familiarity=familiar(0.55),
        consequence=ConsequenceAssessmentV1(architecture=True, production=True),
    )
    assert decision.relationship is RelationshipClassification.NEEDS_CLARIFICATION
    assert decision.clarification_status is ClarificationStatus.REQUIRED
    assert decision.preserve_capture is True
    assert decision.todoist_write_allowed is False
    assert decision.clarification_question is not None
    assert "separate outcome" in decision.clarification_question
    assert "centralized configuration management" in decision.candidate_interpretations


def test_defined_distinct_completion_is_related_non_equivalent() -> None:
    decision = decide_relationship(
        capture="centrally manage ANX customer devices",
        proposed_completion=completion(
            "centralized configuration",
            "devices controlled through approved platform",
        ),
        related_records=(
            RelatedRecordV1(
                record_id="snmp",
                title="Discover devices",
                completion=completion("CMDB discovery", "devices discovered in CMDB"),
            ),
        ),
        familiarity=familiar(),
        consequence=ConsequenceAssessmentV1(),
    )
    assert decision.relationship is RelationshipClassification.RELATED_NON_EQUIVALENT
    assert decision.clarification_status is ClarificationStatus.NOT_REQUIRED


def test_low_history_high_consequence_uses_minimal_evidence_and_clarifies() -> None:
    decision = decide_relationship(
        capture="change production access model",
        proposed_completion=None,
        related_records=(RelatedRecordV1(record_id="access", title="Review access"),),
        familiarity=familiar(0.1),
        consequence=ConsequenceAssessmentV1(
            security=True,
            production=True,
            reversible=False,
        ),
    )
    assert decision.evidence_level is EvidenceLevel.MINIMAL
    assert decision.clarification_status is ClarificationStatus.REQUIRED


def test_confirmed_user_corrections_create_confirmed_pattern() -> None:
    evidence = tuple(
        IntentEvidenceV1(
            evidence_id=f"e{i}",
            context_key="anx",
            interpretation="separate outcome",
            confirmed=True,
            corrected_by_user=i < 2,
        )
        for i in range(4)
    )
    decision = decide_relationship(
        capture="new ANX lifecycle outcome",
        proposed_completion=completion(
            "lifecycle management",
            "lifecycle controls operational",
        ),
        related_records=(),
        familiarity=familiar(),
        consequence=ConsequenceAssessmentV1(),
        evidence=evidence,
    )
    assert decision.evidence_level is EvidenceLevel.CONFIRMED_PATTERN
    assert decision.relationship is RelationshipClassification.DISTINCT_OUTCOME


def test_strong_evidence_requires_two_confirmations() -> None:
    evidence = tuple(
        IntentEvidenceV1(
            evidence_id=f"e{i}",
            context_key="anx",
            interpretation="separate outcome",
            confirmed=True,
        )
        for i in range(2)
    )
    decision = decide_relationship(
        capture="new ANX monitoring outcome",
        proposed_completion=completion("monitoring", "monitoring operational"),
        related_records=(),
        familiarity=familiar(0.75),
        consequence=ConsequenceAssessmentV1(),
        evidence=evidence,
    )
    assert decision.evidence_level is EvidenceLevel.STRONG


def test_stale_and_contradictory_evidence_are_excluded() -> None:
    evidence = (
        IntentEvidenceV1(
            evidence_id="stale",
            context_key="x",
            interpretation="duplicate",
            confirmed=True,
            stale=True,
        ),
        IntentEvidenceV1(
            evidence_id="contradiction",
            context_key="x",
            interpretation="separate",
            confirmed=True,
            contradictory=True,
        ),
    )
    decision = decide_relationship(
        capture="broad vendor migration",
        proposed_completion=None,
        related_records=(RelatedRecordV1(record_id="v", title="vendor assessment"),),
        familiarity=familiar(0.1),
        consequence=ConsequenceAssessmentV1(
            vendor=True,
            external_commitment=True,
        ),
        evidence=evidence,
    )
    assert decision.evidence_level is EvidenceLevel.MINIMAL
    assert decision.clarification_status is ClarificationStatus.REQUIRED


def test_decision_validator_rejects_provider_writes() -> None:
    try:
        ClarificationDecisionV1(
            original_capture="capture",
            related_record_ids=(),
            candidate_interpretations=(),
            material_distinction="none",
            evidence_level=EvidenceLevel.MINIMAL,
            familiarity=familiar(),
            consequence=ConsequenceAssessmentV1(),
            relationship=RelationshipClassification.DISTINCT_OUTCOME,
            clarification_status=ClarificationStatus.NOT_REQUIRED,
            clarification_question=None,
            clarification_reason=None,
            provider_writes=1,
        )
    except ValueError as error:
        assert "provider-write free" in str(error)
    else:
        raise AssertionError("provider writes must be rejected")


def test_required_clarification_requires_a_question() -> None:
    try:
        ClarificationDecisionV1(
            original_capture="capture",
            related_record_ids=("r",),
            candidate_interpretations=("a", "b"),
            material_distinction="unresolved",
            evidence_level=EvidenceLevel.MINIMAL,
            familiarity=familiar(0.1),
            consequence=ConsequenceAssessmentV1(),
            relationship=RelationshipClassification.NEEDS_CLARIFICATION,
            clarification_status=ClarificationStatus.REQUIRED,
            clarification_question=None,
            clarification_reason="required",
        )
    except ValueError as error:
        assert "focused question" in str(error)
    else:
        raise AssertionError("required clarification must include a question")


def test_reprocessing_is_deterministic_and_write_free() -> None:
    kwargs = {
        "capture": "centrally manage ANX customer devices",
        "proposed_completion": None,
        "related_records": (RelatedRecordV1(record_id="naming", title="ANX naming"),),
        "familiarity": familiar(0.5),
        "consequence": ConsequenceAssessmentV1(production=True),
    }
    first = decide_relationship(**kwargs)
    second = decide_relationship(**kwargs)
    assert first == second
    assert first.provider_writes == second.provider_writes == 0


def test_feature_policy_is_disabled_by_default() -> None:
    decision = AdaptiveClarificationPolicyV750().evaluate(
        capture="centrally manage ANX customer devices",
        proposed_completion=None,
        related_records=(),
        familiarity=familiar(),
        consequence=ConsequenceAssessmentV1(),
    )
    assert decision is None


def test_enabled_policy_and_wrapper_preserve_execution_boundary() -> None:
    wrapper = AdaptiveInputProcessingWithClarificationV750(
        policy=AdaptiveClarificationPolicyV750(enabled=True)
    )
    decision = wrapper.evaluate_clarification(
        capture="centrally manage ANX customer devices",
        proposed_completion=None,
        related_records=(RelatedRecordV1(record_id="n", title="ANX naming"),),
        familiarity=familiar(0.4),
        consequence=ConsequenceAssessmentV1(production=True),
    )
    assert decision is not None
    assert decision.provider_writes == 0
    assert decision.todoist_write_allowed is False
    assert wrapper.execution_blocked(decision) is True


def test_wrapper_retains_v62_processing_path() -> None:
    result = AdaptiveInputProcessingWithClarificationV750().process(
        "Create a project plan for an ANX device-management initiative"
    )
    assert result.provider_writes == 0
    assert result.execution_authorized is False
