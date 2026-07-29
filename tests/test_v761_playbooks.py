from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from atlas_ros.contracts.digests import sha256_digest
from atlas_ros.intent_learning_v750 import (
    ClarificationDecisionV1,
    ClarificationStatus,
    ConsequenceAssessmentV1,
    ContextFamiliarityV1,
    EvidenceLevel,
    RelationshipClassification,
)
from atlas_ros.intent_memory_v760 import (
    EvidenceSourceKind,
    FreshnessState,
    GovernedIntentEvidenceV1,
    IntentContextKeyV1,
    IntentScopeV1,
)
from atlas_ros.profile_bundle_v761 import (
    load_profile_or_none,
    validate_profile_minimization,
    write_minimized_bundle,
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
    DelegationMode,
    PreferenceConfirmationState,
    PreferenceLearningInputV1,
    ReliabilityLevel,
    SensitivityLevel,
    UserCommunicationProfileBundleV1,
    UserOverrideState,
    WorkloadDecision,
    WorkloadInputV1,
    build_user_model_projection,
    conflict_accountability_playbook,
    decision_support_playbook,
    decide_preference_learning,
    delegation_playbook,
    explain_adaptation,
    preserve_predecessor_clarification,
    sensitive_discussion_playbook,
    strengthen_career_language,
    workload_playbook,
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

def test_low_risk_reversible_decision_recommends_default() -> None:
    result = decision_support_playbook(
        DecisionSupportInputV1(
            consequence=DecisionConsequence.LOW,
            reversible=True,
            missing_material_facts=False,
            additional_evidence_likely_to_change_outcome=False,
        )
    )
    assert result.recommend_reasonable_default is True
    assert result.clarification_required is False
    assert result.diminishing_returns is True
    assert result.manufactured_urgency is False


def test_high_consequence_missing_facts_still_requires_clarification() -> None:
    result = decision_support_playbook(
        DecisionSupportInputV1(
            consequence=DecisionConsequence.HIGH,
            reversible=False,
            missing_material_facts=True,
            additional_evidence_likely_to_change_outcome=True,
        )
    )
    assert result.recommend_reasonable_default is False
    assert result.clarification_required is True
    assert "consequential_missing_material_facts" in result.reason_codes


def test_predecessor_clarification_is_preserved_unchanged() -> None:
    decision = ClarificationDecisionV1(
        original_capture="Change a production network routing policy",
        related_record_ids=("record:1",),
        candidate_interpretations=("modify policy", "replace policy"),
        material_distinction="The production change boundary is unresolved.",
        evidence_level=EvidenceLevel.PARTIAL,
        familiarity=ContextFamiliarityV1(
            user=0.8,
            domain=0.6,
            project=0.2,
            terminology=0.4,
            evidence_recency=0.4,
            interpretation_consistency=0.3,
        ),
        consequence=ConsequenceAssessmentV1(
            production=True,
            architecture=True,
            reversible=False,
        ),
        relationship=RelationshipClassification.NEEDS_CLARIFICATION,
        clarification_status=ClarificationStatus.REQUIRED,
        clarification_question="Should the existing policy be modified or replaced?",
        clarification_reason="The production change boundary changes the implementation.",
    )
    before = decision.model_dump(mode="json")
    result = preserve_predecessor_clarification(decision)
    assert decision.clarification_status is ClarificationStatus.REQUIRED
    assert result.model_dump(mode="json") == before
    assert result.todoist_write_allowed is False
    assert result.provider_writes == 0


def test_adequately_clear_diplomatic_language_is_preserved() -> None:
    result = conflict_accountability_playbook(
        ConflictAccountabilityInputV1(
            objective_facts_present=True,
            impact_present=True,
            expectation_explicit=True,
            required_action_explicit=True,
            consequence_explicit_when_needed=True,
            desired_outcome_present=True,
            likely_objections_considered=True,
            diplomatic_language_clear=True,
        )
    )
    assert result.needs_strengthening is False
    assert result.preserve_existing_diplomacy is True
    assert result.aggression_increase_required is False


def test_weak_verbs_strengthen_only_when_supported() -> None:
    result = strengthen_career_language(
        statement="I helped the team deliver the migration and supported stakeholder updates.",
        evidence_supported_replacements={"helped": "led"},
    )
    assert "led the team" in result.revised
    assert "supported stakeholder" in result.revised
    assert result.replacements == (("helped", "led"),)
    assert result.unsupported_replacements_skipped == ("supported",)
    assert result.invented_metrics is False


def test_team_credit_is_preserved() -> None:
    result = strengthen_career_language(
        statement="I supported the team through the cutover.",
        evidence_supported_replacements={"supported": "directed"},
        preserve_team_credit=True,
    )
    assert "team" in result.revised
    assert result.team_credit_preserved is True


def test_delegation_varies_by_capability_and_consequence() -> None:
    developing = delegation_playbook(
        DelegationInputV1(
            capability=0.55,
            confidence=0.50,
            consequence=DecisionConsequence.MODERATE,
            outcome_clarity=0.85,
            checkpoints_available=True,
            accountability_belongs_to_other=True,
        )
    )
    high_consequence = delegation_playbook(
        DelegationInputV1(
            capability=0.70,
            confidence=0.80,
            consequence=DecisionConsequence.HIGH,
            outcome_clarity=0.60,
            checkpoints_available=True,
            accountability_belongs_to_other=True,
        )
    )
    capable = delegation_playbook(
        DelegationInputV1(
            capability=0.95,
            confidence=0.90,
            consequence=DecisionConsequence.LOW,
            outcome_clarity=0.95,
            checkpoints_available=False,
            accountability_belongs_to_other=True,
        )
    )
    assert developing.mode is DelegationMode.COACH_WITH_CHECKPOINTS
    assert high_consequence.mode is DelegationMode.DIRECT_INSTRUCTION
    assert capable.mode is DelegationMode.DELEGATE


def test_workload_playbook_protects_ownership_and_priority() -> None:
    delegate = workload_playbook(
        WorkloadInputV1(
            ownership_is_mine=False,
            higher_priority_displaced=False,
            delegable=True,
            requester_retains_accountability=True,
            minimum_success_defined=True,
            impact_exceeds_effort=True,
            helping_reduces_other_accountability=False,
        )
    )
    decline = workload_playbook(
        WorkloadInputV1(
            ownership_is_mine=False,
            higher_priority_displaced=True,
            delegable=False,
            requester_retains_accountability=False,
            minimum_success_defined=False,
            impact_exceeds_effort=False,
            helping_reduces_other_accountability=True,
        )
    )
    assert delegate.decision is WorkloadDecision.DELEGATE
    assert decline.decision is WorkloadDecision.DECLINE
    assert decline.displaced_priority_must_be_named is True


def test_sensitive_discussion_uses_brief_acknowledgment_without_diagnosis() -> None:
    result = sensitive_discussion_playbook(
        acknowledgment="That situation has a real personal impact."
    )
    assert result.practical_analysis_required is True
    assert result.diagnostic_language_allowed is False
    assert result.inferred_mental_state_allowed is False
