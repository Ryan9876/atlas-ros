from atlas_ros.clarification_evaluation_v752 import (
    ClarificationEvaluationCaseV1,
    ClarificationEvaluationEngineV752,
    ClarificationOutcomeV1,
    CounterfactualDecisionV1,
    EvaluationMode,
    assess_question,
    build_event,
)
from atlas_ros.intent_learning_v750 import (
    ClarificationStatus,
    CompletionDimensionsV1,
    ConsequenceAssessmentV1,
    ContextFamiliarityV1,
    EvidenceLevel,
    RelatedRecordV1,
    RelationshipClassification,
    decide_relationship,
)


def familiar(score: float = 0.8) -> ContextFamiliarityV1:
    return ContextFamiliarityV1(
        user=0.95,
        domain=score,
        project=score,
        terminology=score,
        evidence_recency=score,
        interpretation_consistency=score,
    )


def completion(outcome: str, done: str) -> CompletionDimensionsV1:
    return CompletionDimensionsV1(
        intended_outcome=outcome,
        scope="minimized fixture scope",
        definition_of_done=done,
        accountable_owner="Ryan",
        ryan_management_action="review",
        execution_evidence="verified evidence",
        completion_boundary=done,
    )


def test_disabled_mode_is_predecessor_equivalent() -> None:
    engine = ClarificationEvaluationEngineV752()
    assert engine.evaluate(snapshot_id="s1", cases=(), outcomes=()) is None


def test_identical_inputs_produce_identical_report_digest() -> None:
    decision = decide_relationship(
        capture="centrally manage ANX customer devices",
        proposed_completion=None,
        related_records=(
            RelatedRecordV1(record_id="naming", title="ANX naming"),
            RelatedRecordV1(record_id="snmp", title="SNMP discovery"),
        ),
        familiarity=familiar(0.5),
        consequence=ConsequenceAssessmentV1(architecture=True, production=True),
    )
    assert decision.clarification_status is ClarificationStatus.REQUIRED
    event = build_event(
        operation_id="op-1",
        correlation_id="corr-1",
        snapshot_id="snapshot-1",
        original_capture=decision.original_capture,
        related_record_ids=decision.related_record_ids,
        candidate_interpretations=decision.candidate_interpretations,
        initial_decision=decision,
        evidence_level=decision.evidence_level,
        familiarity=decision.familiarity,
        consequence=decision.consequence,
        question=decision.clarification_question,
        question_basis=decision.clarification_reason,
        user_response="Separate outcome for centralized configuration management.",
        final_confirmed_interpretation="centralized configuration management",
        final_classification=RelationshipClassification.RELATED_NON_EQUIVALENT,
        final_destination="portfolio-project",
        execution_path_effect="prevented incorrect suppression",
        provider_write_count=0,
        todoist_write_count=0,
    )
    quality = assess_question(
        decision=decision,
        user_response=event.user_response,
        final_relationship=event.final_classification,
    )
    case = ClarificationEvaluationCaseV1(
        case_id="anx-central-management",
        provenance="accepted minimized regression fixture",
        event=event,
        counterfactual=CounterfactualDecisionV1(
            likely_relationship_without_clarification=RelationshipClassification.PARAPHRASED_DUPLICATE,
            confirmed_relationship=event.final_classification,
            likely_execution_path_effect="incorrect suppression",
            confirmed_execution_path_effect=event.execution_path_effect,
        ),
        question_quality=quality,
    )
    outcome = ClarificationOutcomeV1(
        case_id=case.case_id,
        clarification_required=True,
        resolved_with_one_question=True,
        user_corrected_interpretation=True,
        material_change=True,
        prevented_false_duplicate=True,
        prevented_task_suppression=True,
    )
    engine = ClarificationEvaluationEngineV752(mode=EvaluationMode.SHADOW)
    first = engine.evaluate(snapshot_id="snapshot-1", cases=(case,), outcomes=(outcome,))
    second = engine.evaluate(snapshot_id="snapshot-1", cases=(case,), outcomes=(outcome,))
    assert first is not None and second is not None
    assert first == second
    assert first.deterministic_digest == second.deterministic_digest
    assert first.provider_writes == first.todoist_writes == 0


def test_jira_customization_and_integration_are_related_but_separate() -> None:
    decision = decide_relationship(
        capture="Implement Jira integration",
        proposed_completion=completion("Jira integration", "integration operational"),
        related_records=(
            RelatedRecordV1(
                record_id="jira-customization",
                title="Customize Jira workflow",
                completion=completion("Jira customization", "workflow customized"),
            ),
        ),
        familiarity=familiar(),
        consequence=ConsequenceAssessmentV1(),
    )
    assert decision.relationship is RelationshipClassification.RELATED_NON_EQUIVALENT


def test_true_and_paraphrased_duplicates_remain_predecessor_decisions() -> None:
    proposed = completion("standard naming", "approved standard")
    exact = decide_relationship(
        capture="Define naming standard",
        proposed_completion=proposed,
        related_records=(
            RelatedRecordV1(
                record_id="same",
                title="Define naming standard",
                completion=proposed,
            ),
        ),
        familiarity=familiar(),
        consequence=ConsequenceAssessmentV1(),
    )
    paraphrase = decide_relationship(
        capture="Create the naming standard",
        proposed_completion=proposed,
        related_records=(
            RelatedRecordV1(
                record_id="same",
                title="Define naming standard",
                completion=proposed,
            ),
        ),
        familiarity=familiar(),
        consequence=ConsequenceAssessmentV1(),
    )
    assert exact.relationship is RelationshipClassification.EXACT_DUPLICATE
    assert paraphrase.relationship is RelationshipClassification.PARAPHRASED_DUPLICATE


def test_high_consequence_ambiguity_preserves_clarification_control() -> None:
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
    assessment = assess_question(
        decision=decision,
        user_response=None,
        final_relationship=decision.relationship,
    )
    assert decision.clarification_status is ClarificationStatus.REQUIRED
    assert assessment.preserves_consequence_controls is True


def test_strong_evidence_can_avoid_clarification_without_evaluation_authority() -> None:
    decision = decide_relationship(
        capture="Create monitoring outcome",
        proposed_completion=completion("monitoring", "monitoring operational"),
        related_records=(),
        familiarity=familiar(0.9),
        consequence=ConsequenceAssessmentV1(),
    )
    assert decision.evidence_level in {EvidenceLevel.STRONG, EvidenceLevel.PARTIAL}
    assert decision.clarification_status is ClarificationStatus.NOT_REQUIRED
    assert decision.provider_writes == 0


def test_counterfactual_rejects_authority_and_writes() -> None:
    try:
        CounterfactualDecisionV1(
            likely_relationship_without_clarification=RelationshipClassification.EXACT_DUPLICATE,
            confirmed_relationship=RelationshipClassification.RELATED_NON_EQUIVALENT,
            likely_execution_path_effect="suppression",
            confirmed_execution_path_effect="separate outcome",
            authoritative=True,
        )
    except ValueError as error:
        assert "cannot be authoritative" in str(error)
    else:
        raise AssertionError("counterfactual output must remain non-authoritative")
