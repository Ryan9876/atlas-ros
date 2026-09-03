"""Context-specific communication playbooks for Atlas ROS v7.6.1."""
from __future__ import annotations

from atlas_ros.contracts.digests import sha256_digest
from atlas_ros.user_communication_contracts_v761 import (
    AdaptationInspectionViewV1,
    CareerLanguageResultV1,
    CompiledCommunicationPolicyV1,
    ConflictAccountabilityInputV1,
    ConflictAccountabilityResultV1,
    DecisionConsequence,
    DecisionSupportInputV1,
    DecisionSupportResultV1,
    DelegationInputV1,
    DelegationMode,
    DelegationResultV1,
    PreferenceLearningDecisionV1,
    PreferenceLearningInputV1,
    SensitiveDiscussionResultV1,
    WorkloadDecision,
    WorkloadInputV1,
    WorkloadResultV1,
)


def decision_support_playbook(value: DecisionSupportInputV1) -> DecisionSupportResultV1:
    consequential = value.consequence is DecisionConsequence.HIGH or not value.reversible
    reasons: list[str] = []
    if consequential and value.missing_material_facts:
        reasons.append("consequential_missing_material_facts")
        return DecisionSupportResultV1(
            recommend_reasonable_default=False,
            clarification_required=True,
            diminishing_returns=False,
            reason_codes=tuple(reasons),
            next_action="Obtain the missing material fact before deciding.",
        )
    recommend_default = value.reversible and value.consequence is DecisionConsequence.LOW
    if recommend_default:
        reasons.append("low_risk_reversible_default")
    diminishing = not value.additional_evidence_likely_to_change_outcome
    if diminishing:
        reasons.append("additional_analysis_unlikely_to_change_outcome")
    if value.delay_has_material_cost:
        reasons.append("delay_has_material_cost")
    next_action = (
        "Choose the reasonable default and define a reconsideration trigger."
        if recommend_default
        else "Select the best-supported option and document the key assumption."
    )
    return DecisionSupportResultV1(
        recommend_reasonable_default=recommend_default,
        clarification_required=False,
        diminishing_returns=diminishing,
        reason_codes=tuple(reasons),
        next_action=next_action,
    )


def conflict_accountability_playbook(
    value: ConflictAccountabilityInputV1,
) -> ConflictAccountabilityResultV1:
    hidden: list[str] = []
    checks = {
        "objective_facts": value.objective_facts_present,
        "impact": value.impact_present,
        "expectation": value.expectation_explicit,
        "required_action": value.required_action_explicit,
        "consequence": value.consequence_explicit_when_needed,
        "desired_outcome": value.desired_outcome_present,
        "likely_objections": value.likely_objections_considered,
    }
    hidden.extend(name for name, present in checks.items() if not present)
    return ConflictAccountabilityResultV1(
        needs_strengthening=bool(hidden),
        hidden_elements=tuple(hidden),
        preserve_existing_diplomacy=value.diplomatic_language_clear,
    )


def delegation_playbook(value: DelegationInputV1) -> DelegationResultV1:
    high_consequence = value.consequence is DecisionConsequence.HIGH
    accountability_gap = value.accountability_belongs_to_other and value.support_becoming_rescue
    coaching_gap = value.capability < 0.75 or value.confidence < 0.65
    reasons: list[str] = []
    if accountability_gap:
        reasons.append("support_is_becoming_rescue")
    if value.outcome_clarity < 0.70:
        reasons.append("outcome_requires_clarification")
    if high_consequence and (value.capability < 0.80 or value.outcome_clarity < 0.80):
        mode = DelegationMode.DIRECT_INSTRUCTION
        reasons.append("high_consequence_requires_tighter_control")
    elif coaching_gap:
        mode = DelegationMode.COACH_WITH_CHECKPOINTS
        reasons.append("capability_or_confidence_requires_coaching")
    elif value.accountability_belongs_to_other:
        mode = DelegationMode.DELEGATE
        reasons.append("accountability_belongs_to_other")
    else:
        mode = DelegationMode.RETAIN_OWNERSHIP
        reasons.append("accountability_remains_with_manager")
    checkpoints = mode in {
        DelegationMode.COACH_WITH_CHECKPOINTS,
        DelegationMode.DIRECT_INSTRUCTION,
    }
    if checkpoints and not value.checkpoints_available:
        reasons.append("checkpoints_must_be_created")
    return DelegationResultV1(
        mode=mode,
        checkpoints_required=checkpoints,
        accountability_gap=accountability_gap,
        coaching_gap=coaching_gap,
        rescue_risk=value.support_becoming_rescue,
        reason_codes=tuple(reasons),
    )


def strengthen_career_language(
    *,
    statement: str,
    evidence_supported_replacements: dict[str, str],
    preserve_team_credit: bool = True,
) -> CareerLanguageResultV1:
    weak_verbs = ("helped", "supported", "assisted", "worked on", "was involved in")
    revised = statement
    replacements: list[tuple[str, str]] = []
    skipped: list[str] = []
    for weak in weak_verbs:
        if weak not in revised.casefold():
            continue
        replacement = evidence_supported_replacements.get(weak)
        if replacement:
            revised = _replace_casefold(revised, weak, replacement)
            replacements.append((weak, replacement))
        else:
            skipped.append(weak)
    return CareerLanguageResultV1(
        original=statement,
        revised=revised,
        replacements=tuple(replacements),
        unsupported_replacements_skipped=tuple(skipped),
        team_credit_preserved=preserve_team_credit,
    )


def workload_playbook(value: WorkloadInputV1) -> WorkloadResultV1:
    reasons: list[str] = []
    if not value.ownership_is_mine and value.delegable:
        decision = WorkloadDecision.DELEGATE
        reasons.append("ownership_belongs_elsewhere")
    elif value.helping_reduces_other_accountability:
        decision = WorkloadDecision.DECLINE
        reasons.append("help_would_absorb_another_persons_accountability")
    elif value.higher_priority_displaced and not value.impact_exceeds_effort:
        decision = WorkloadDecision.MINIMUM_SUCCESS
        reasons.append("higher_priority_would_be_displaced")
    else:
        decision = WorkloadDecision.ACCEPT
        reasons.append("ownership_and_impact_support_acceptance")
    if not value.requester_retains_accountability:
        reasons.append("requester_accountability_is_unclear")
    return WorkloadResultV1(
        decision=decision,
        reason_codes=tuple(reasons),
        minimum_success_required=(
            decision is WorkloadDecision.MINIMUM_SUCCESS or not value.minimum_success_defined
        ),
        displaced_priority_must_be_named=value.higher_priority_displaced,
    )


def sensitive_discussion_playbook(*, acknowledgment: str) -> SensitiveDiscussionResultV1:
    normalized = acknowledgment.strip()
    if not normalized:
        raise ValueError("a brief acknowledgment is required")
    if len(normalized) > 180:
        raise ValueError("acknowledgment must remain brief")
    return SensitiveDiscussionResultV1(acknowledgment=normalized)


def explain_adaptation(policy: CompiledCommunicationPolicyV1) -> AdaptationInspectionViewV1:
    reasons: list[str] = []
    if policy.current_instruction_override:
        reasons.append("current_instruction_override")
    if policy.live_authority_override:
        reasons.append("live_authority_override")
    if policy.adaptation_applied:
        reasons.append("confirmed_profile_preferences_applied")
    else:
        reasons.append("safe_baseline_fallback")
    return AdaptationInspectionViewV1(
        policy_digest=policy.deterministic_digest,
        context=policy.context,
        adaptation_applied=policy.adaptation_applied,
        reason_codes=tuple(reasons),
        preference_identity_digests=tuple(
            sha256_digest(identifier) for identifier in policy.applied_preference_ids
        ),
    )


def _replace_casefold(value: str, old: str, new: str) -> str:
    lowered = value.casefold()
    target = old.casefold()
    start = lowered.find(target)
    while start >= 0:
        value = value[:start] + new + value[start + len(old) :]
        lowered = value.casefold()
        start = lowered.find(target, start + len(new))
    return value


def decide_preference_learning(
    value: PreferenceLearningInputV1,
) -> PreferenceLearningDecisionV1:
    qualifying: list[str] = []
    disqualifying: list[str] = []
    if value.explicit_user_statement:
        qualifying.append("explicit_user_preference")
    if value.user_behavior_correction:
        qualifying.append("user_corrected_behavior")
    if value.repeated_same_selection_count >= 3:
        qualifying.append("repeated_concrete_selection")
    if value.assessment_interpretation_explicitly_confirmed:
        qualifying.append("assessment_interpretation_confirmed")
    if value.accepted_single_response:
        disqualifying.append("single_acceptance_is_insufficient")
    if value.user_did_not_object:
        disqualifying.append("non_objection_is_insufficient")
    if value.generic_assessment_description:
        disqualifying.append("generic_assessment_is_insufficient")
    if value.inferred_emotion_or_motive:
        disqualifying.append("emotion_or_motive_inference_is_prohibited")
    if value.single_sensitive_conversation:
        disqualifying.append("single_sensitive_conversation_is_insufficient")
    if value.third_party_description:
        disqualifying.append("third_party_description_is_insufficient")
    allowed = bool(qualifying) and not (
        value.inferred_emotion_or_motive or value.third_party_description
    )
    reasons = tuple(qualifying + disqualifying)
    return PreferenceLearningDecisionV1(
        stable_preference_allowed=allowed,
        provisional_only=not allowed,
        reason_codes=reasons or ("insufficient_evidence",),
    )
