from __future__ import annotations

import json

from atlas_ros.contracts.digests import sha256_digest
from atlas_ros.intent_memory_v760 import (
    EvidenceSourceKind,
    FreshnessState,
    GovernedIntentEvidenceV1,
    IntentContextKeyV1,
    IntentScopeV1,
)
from atlas_ros.user_communication_policy_v761 import (
    UserCommunicationFeaturePolicyV761,
)
from atlas_ros.user_communication_v761 import (
    AdaptationMode,
    CommunicationContext,
    CommunicationEvidenceType,
    CommunicationPreferenceV1,
    CommunicationSourceEvidenceV1,
    ConflictAccountabilityInputV1,
    ContradictionState,
    DecisionConsequence,
    DecisionSupportInputV1,
    DelegationInputV1,
    PreferenceConfirmationState,
    PreferenceLearningInputV1,
    ReliabilityLevel,
    SensitivityLevel,
    UserCommunicationProfileBundleV1,
    UserOverrideState,
    build_user_model_projection,
    conflict_accountability_playbook,
    decide_preference_learning,
    decision_support_playbook,
    delegation_playbook,
    explain_adaptation,
)

NOW = "2026-07-29T18:00:00-04:00"
REVIEW = "2026-10-29T18:00:00-04:00"
USER_ID = "385d872b-594c-815b-83b6-00020c5022f3"
WORKSPACE_ID = "276b8344-ad2c-8157-b705-00033d541c9e"


def governed_evidence(
    evidence_id: str,
    *,
    behavior: str,
) -> GovernedIntentEvidenceV1:
    return GovernedIntentEvidenceV1(
        evidence_id=evidence_id,
        context_key=IntentContextKeyV1(
            context_id=f"context:{evidence_id}",
            scope=IntentScopeV1(user_id=USER_ID),
            behavior=behavior,
        ),
        confirmed_interpretation=behavior,
        represented_behavior=behavior,
        source_kind=EvidenceSourceKind.CONFIRMED_INTERACTION,
        source_reference=f"governed:{evidence_id}",
        source_digest=sha256_digest(f"source:{evidence_id}"),
        confirmation_count=3,
        correction_count=0,
        contradiction_count=0,
        confidence=0.95,
        first_confirmed_at="2026-06-01T12:00:00-04:00",
        last_confirmed_at=NOW,
        freshness_state=FreshnessState.CURRENT,
        inference_eligible=True,
        provenance=("v7.6.0 governed evidence",),
    )


def source_evidence(
    source_id: str,
    evidence_id: str,
    *,
    evidence_type: CommunicationEvidenceType = CommunicationEvidenceType.EXPLICIT_PREFERENCE,
    confirmation: PreferenceConfirmationState = PreferenceConfirmationState.USER_CONFIRMED,
    sensitivity: SensitivityLevel = SensitivityLevel.STANDARD,
) -> CommunicationSourceEvidenceV1:
    return CommunicationSourceEvidenceV1(
        source_id=source_id,
        evidence_type=evidence_type,
        governed_reference=f"governed:{evidence_id}",
        evidence_date=NOW,
        reliability=ReliabilityLevel.HIGH,
        limitations=("minimized behavior evidence",),
        confirmation_state=confirmation,
        sensitivity=sensitivity,
        provenance=("current user instruction",),
        governed_intent_evidence_ids=(evidence_id,),
    )


def preference(
    preference_id: str,
    source_id: str,
    *,
    context: CommunicationContext = CommunicationContext.GENERAL,
    confirmation: PreferenceConfirmationState = PreferenceConfirmationState.USER_CONFIRMED,
    confidence: float = 0.95,
    contradiction: ContradictionState = ContradictionState.NONE,
    sensitivity: SensitivityLevel = SensitivityLevel.STANDARD,
    override: UserOverrideState = UserOverrideState.DEFAULT,
) -> CommunicationPreferenceV1:
    return CommunicationPreferenceV1(
        preference_id=preference_id,
        practical_description="Use an outcome-first response structure.",
        applicable_contexts=(context,),
        preferred_behaviors=("Lead with the recommendation before supporting detail.",),
        avoided_behaviors=("burying the recommendation",),
        confidence=confidence,
        confirmation_state=confirmation,
        evidence_references=(source_id,),
        created_at=NOW,
        reviewed_at=NOW,
        user_override_state=override,
        sensitivity=sensitivity,
        contradiction_state=contradiction,
    )


def profile_bundle(
    *,
    enabled: bool = True,
    review_due: str = REVIEW,
    preferences: tuple[CommunicationPreferenceV1, ...] | None = None,
    sources: tuple[CommunicationSourceEvidenceV1, ...] | None = None,
    evidence: tuple[GovernedIntentEvidenceV1, ...] | None = None,
) -> UserCommunicationProfileBundleV1:
    sources = sources or (source_evidence("source:conclusion", "intent:conclusion"),)
    preferences = preferences or (preference("pref:conclusion", sources[0].source_id),)
    evidence = evidence or (
        governed_evidence("intent:conclusion", behavior="conclusion-first responses"),
    )
    projection = build_user_model_projection(
        projection_id="projection:ryan:v1",
        profile_version="ryan-v1",
        user_id=USER_ID,
        workspace_id=WORKSPACE_ID,
        generated_at=NOW,
        preferences=tuple(sorted(preferences, key=lambda item: item.preference_id)),
        source_evidence=tuple(sorted(sources, key=lambda item: item.source_id)),
        governed_evidence=evidence,
    )
    return UserCommunicationProfileBundleV1(
        profile_version="ryan-v1",
        user_id=USER_ID,
        workspace_id=WORKSPACE_ID,
        repository_binding="Ryan9876/atlas-ros",
        generated_at=NOW,
        review_due_at=review_due,
        global_enabled=enabled,
        preferences=tuple(sorted(preferences, key=lambda item: item.preference_id)),
        source_evidence=tuple(sorted(sources, key=lambda item: item.source_id)),
        projection=projection,
    )

def test_diminishing_returns_never_manufactures_deadline() -> None:
    result = decision_support_playbook(
        DecisionSupportInputV1(
            consequence=DecisionConsequence.MODERATE,
            reversible=True,
            missing_material_facts=False,
            additional_evidence_likely_to_change_outcome=False,
            delay_has_material_cost=False,
        )
    )
    assert result.diminishing_returns is True
    assert result.manufactured_urgency is False
    assert "deadline" not in result.next_action.casefold()


def test_accountability_message_flags_hidden_expectation() -> None:
    result = conflict_accountability_playbook(
        ConflictAccountabilityInputV1(
            objective_facts_present=True,
            impact_present=True,
            expectation_explicit=False,
            required_action_explicit=False,
            consequence_explicit_when_needed=True,
            desired_outcome_present=True,
            likely_objections_considered=True,
            diplomatic_language_clear=False,
        )
    )
    assert result.needs_strengthening is True
    assert result.hidden_elements == ("expectation", "required_action")
    assert result.aggression_increase_required is False


def test_coaching_and_accountability_gaps_remain_distinct() -> None:
    result = delegation_playbook(
        DelegationInputV1(
            capability=0.90,
            confidence=0.90,
            consequence=DecisionConsequence.LOW,
            outcome_clarity=0.95,
            checkpoints_available=False,
            accountability_belongs_to_other=True,
            support_becoming_rescue=True,
        )
    )
    assert result.coaching_gap is False
    assert result.accountability_gap is True
    assert result.rescue_risk is True


def test_contradictory_assessment_preferences_are_preserved_and_excluded() -> None:
    source_a = source_evidence(
        "source:assessment-a",
        "intent:assessment-a",
        evidence_type=CommunicationEvidenceType.ASSESSMENT,
        confirmation=PreferenceConfirmationState.ASSESSMENT_SUPPORTED,
    )
    source_b = source_evidence(
        "source:assessment-b",
        "intent:assessment-b",
        evidence_type=CommunicationEvidenceType.ASSESSMENT,
        confirmation=PreferenceConfirmationState.CONTRADICTED,
    )
    pref_a = preference(
        "pref:assessment-a",
        source_a.source_id,
        confirmation=PreferenceConfirmationState.ASSESSMENT_SUPPORTED,
        contradiction=ContradictionState.OPEN,
    )
    pref_b = preference(
        "pref:assessment-b",
        source_b.source_id,
        confirmation=PreferenceConfirmationState.CONTRADICTED,
        contradiction=ContradictionState.OPEN,
    )
    bundle = profile_bundle(
        preferences=(pref_a, pref_b),
        sources=(source_a, source_b),
        evidence=(
            governed_evidence("intent:assessment-a", behavior="assessment tendency a"),
            governed_evidence("intent:assessment-b", behavior="assessment tendency b"),
        ),
    )
    assert bundle.projection.contradiction_preference_ids == (
        "pref:assessment-a",
        "pref:assessment-b",
    )
    result = UserCommunicationFeaturePolicyV761(
        mode=AdaptationMode.ADAPTATION,
        selected_profile_version="ryan-v1",
    ).compile(
        context=CommunicationContext.GENERAL,
        now=NOW,
        request_user_id=USER_ID,
        request_workspace_id=WORKSPACE_ID,
        profile=bundle,
    )
    assert result.adaptation_applied is False
    assert result.excluded_preference_ids == (
        "pref:assessment-a",
        "pref:assessment-b",
    )


def test_adaptation_trace_contains_only_digests_and_reason_codes() -> None:
    result = UserCommunicationFeaturePolicyV761(
        mode=AdaptationMode.ADAPTATION,
        selected_profile_version="ryan-v1",
    ).compile(
        context=CommunicationContext.GENERAL,
        now=NOW,
        request_user_id=USER_ID,
        request_workspace_id=WORKSPACE_ID,
        profile=profile_bundle(),
    )
    trace = explain_adaptation(result)
    payload = json.dumps(trace.model_dump(mode="json"))
    assert trace.redacted is True
    assert trace.raw_profile_content_present is False
    assert "outcome-first" not in payload
    assert "Lead with the recommendation" not in payload
    assert all(len(value) == 64 for value in trace.preference_identity_digests)


def test_learning_boundaries_require_qualifying_user_evidence() -> None:
    explicit = decide_preference_learning(
        PreferenceLearningInputV1(explicit_user_statement=True)
    )
    repeated = decide_preference_learning(
        PreferenceLearningInputV1(repeated_same_selection_count=3)
    )
    silence = decide_preference_learning(
        PreferenceLearningInputV1(user_did_not_object=True)
    )
    third_party = decide_preference_learning(
        PreferenceLearningInputV1(
            explicit_user_statement=True,
            third_party_description=True,
        )
    )
    assert explicit.stable_preference_allowed is True
    assert repeated.stable_preference_allowed is True
    assert silence.stable_preference_allowed is False
    assert silence.provisional_only is True
    assert third_party.stable_preference_allowed is False


def test_restricted_preference_does_not_leak_to_unrelated_context() -> None:
    source = source_evidence(
        "source:sensitive",
        "intent:sensitive",
        sensitivity=SensitivityLevel.RESTRICTED,
    )
    pref = preference(
        "pref:sensitive",
        source.source_id,
        context=CommunicationContext.GENERAL,
        sensitivity=SensitivityLevel.RESTRICTED,
    )
    bundle = profile_bundle(
        preferences=(pref,),
        sources=(source,),
        evidence=(governed_evidence("intent:sensitive", behavior="sensitive behavior"),),
    )
    result = UserCommunicationFeaturePolicyV761(
        mode=AdaptationMode.ADAPTATION,
        selected_profile_version="ryan-v1",
    ).compile(
        context=CommunicationContext.GENERAL,
        now=NOW,
        request_user_id=USER_ID,
        request_workspace_id=WORKSPACE_ID,
        profile=bundle,
    )
    assert result.adaptation_applied is False
    assert result.applied_preference_ids == ()
