from atlas_ros import clarification_evaluation_v752 as evaluation
from atlas_ros import intent_learning_v750 as intent
from atlas_ros.contracts.digests import sha256_digest


def familiarity() -> intent.ContextFamiliarityV1:
    return intent.ContextFamiliarityV1(
        user=0.8,
        domain=0.7,
        project=0.7,
        terminology=0.8,
        evidence_recency=0.8,
        interpretation_consistency=0.7,
    )


def predecessor() -> intent.ClarificationDecisionV1:
    return intent.decide_relationship(
        capture="Centrally manage ANX customer devices",
        proposed_completion=None,
        related_records=(),
        familiarity=familiarity(),
        consequence=intent.ConsequenceAssessmentV1(
            production=True,
            architecture=True,
        ),
    )


def event_for(
    decision: intent.ClarificationDecisionV1,
) -> evaluation.ClarificationEventV1:
    decision_digest = sha256_digest(decision.model_dump(mode="json"))
    return evaluation.ClarificationEventV1(
        operation_id="op-v752-1",
        correlation_id="workspace-redacted:1",
        snapshot_digest="a" * 64,
        original_capture=decision.original_capture,
        related_record_ids=decision.related_record_ids,
        candidate_interpretations=decision.candidate_interpretations,
        initial_decision_digest=decision_digest,
        evidence_level=decision.evidence_level.value,
        familiarity_digest=sha256_digest(
            decision.familiarity.model_dump(mode="json")
        ),
        consequence_digest=sha256_digest(
            decision.consequence.model_dump(mode="json")
        ),
        question=decision.clarification_question,
        question_basis=decision.clarification_reason,
        user_response="This is a separate centralized configuration outcome.",
        final_confirmed_interpretation=(
            "separate centralized configuration outcome"
        ),
        final_classification=intent.RelationshipClassification.DISTINCT_OUTCOME.value,
        execution_path_effect="suppression_prevented",
    )


def quality() -> evaluation.QuestionQualityAssessmentV1:
    return evaluation.QuestionQualityAssessmentV1(
        demonstrates_understanding=True,
        identifies_material_ambiguity=True,
        one_focused_question=True,
        avoids_generic_language=True,
        avoids_known_information_request=True,
        minimizes_interaction_burden=True,
        materially_changes_or_confirms_decision=True,
        preserves_consequence_controls=True,
        preserves_reversibility_controls=True,
    )


def test_disabled_policy_is_equivalent_to_predecessor() -> None:
    decision = predecessor()
    assert decision.clarification_status is intent.ClarificationStatus.NOT_REQUIRED
    result = evaluation.ClarificationEvaluationPolicyV752().evaluate(
        event=event_for(decision),
        predecessor_decision=decision,
        counterfactual=evaluation.CounterfactualDecisionV1(
            likely_classification=(
                intent.RelationshipClassification.PARAPHRASED_DUPLICATE.value
            ),
            differs_from_confirmed=True,
        ),
        question_quality=quality(),
        outcome=evaluation.ClarificationOutcomeV1(),
        case_id="disabled",
    )
    assert result is None
    assert decision.provider_writes == 0
    assert decision.todoist_write_allowed is False


def test_shadow_evaluation_is_inert_and_digest_bound() -> None:
    decision = predecessor()
    case = evaluation.ClarificationEvaluationPolicyV752(mode="shadow").evaluate(
        event=event_for(decision),
        predecessor_decision=decision,
        counterfactual=evaluation.CounterfactualDecisionV1(
            likely_classification=(
                intent.RelationshipClassification.PARAPHRASED_DUPLICATE.value
            ),
            differs_from_confirmed=True,
            confidence_basis=(
                "related wording",
                "missing completion equivalence",
            ),
        ),
        question_quality=quality(),
        outcome=evaluation.ClarificationOutcomeV1(
            corrected_by_user=True,
            resolved_with_one_question=True,
            material_change=True,
            false_duplicate_prevented=True,
            task_suppression_prevented=True,
        ),
        case_id="anx-central-management",
    )
    assert case is not None
    assert case.counterfactual.non_authoritative is True
    assert case.counterfactual.routing_allowed is False
    assert case.counterfactual.execution_authorized is False
    assert case.event.provider_write_count == 0
    assert case.event.todoist_write_count == 0


def test_identical_inputs_produce_identical_report_digest() -> None:
    decision = predecessor()
    policy = evaluation.ClarificationEvaluationPolicyV752(mode="shadow")
    event = event_for(decision)
    counterfactual = evaluation.CounterfactualDecisionV1(
        likely_classification=(
            intent.RelationshipClassification.PARAPHRASED_DUPLICATE.value
        ),
        differs_from_confirmed=True,
    )
    outcome = evaluation.ClarificationOutcomeV1(
        resolved_with_one_question=True,
        material_change=True,
        task_suppression_prevented=True,
    )
    first_case = policy.evaluate(
        event=event,
        predecessor_decision=decision,
        counterfactual=counterfactual,
        question_quality=quality(),
        outcome=outcome,
        case_id="deterministic",
    )
    second_case = policy.evaluate(
        event=event,
        predecessor_decision=decision,
        counterfactual=counterfactual,
        question_quality=quality(),
        outcome=outcome,
        case_id="deterministic",
    )
    assert first_case is not None and second_case is not None
    first = evaluation.build_report(
        feature_mode="shadow",
        snapshot_digest="a" * 64,
        cases=(first_case,),
    )
    second = evaluation.build_report(
        feature_mode="shadow",
        snapshot_digest="a" * 64,
        cases=(second_case,),
    )
    assert first == second
    assert first.deterministic_digest == second.deterministic_digest
    assert first.provider_write_count == first.todoist_write_count == 0


def test_provider_writes_are_rejected() -> None:
    decision = predecessor()
    try:
        evaluation.ClarificationEventV1(
            operation_id="op",
            correlation_id="redacted",
            snapshot_digest="a" * 64,
            original_capture=decision.original_capture,
            initial_decision_digest=sha256_digest(
                decision.model_dump(mode="json")
            ),
            evidence_level=intent.EvidenceLevel.MINIMAL.value,
            familiarity_digest="b" * 64,
            consequence_digest="c" * 64,
            provider_write_count=1,
        )
    except ValueError as error:
        assert "provider-write free" in str(error)
    else:
        raise AssertionError("evaluation events must reject provider writes")


def test_question_quality_counts_all_governed_checks() -> None:
    assessment = quality()
    assert assessment.passed_checks == 9
