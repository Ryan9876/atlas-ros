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

def test_feature_disabled_is_equivalent_to_v760_baseline() -> None:
    baseline = UserCommunicationFeaturePolicyV761().compile(
        context=CommunicationContext.GENERAL,
        now=NOW,
        request_user_id=USER_ID,
        request_workspace_id=WORKSPACE_ID,
    )
    with_profile = UserCommunicationFeaturePolicyV761().compile(
        context=CommunicationContext.GENERAL,
        now=NOW,
        request_user_id=USER_ID,
        request_workspace_id=WORKSPACE_ID,
        profile=profile_bundle(enabled=True),
    )
    assert baseline.directives == with_profile.directives
    assert baseline.avoided_patterns == with_profile.avoided_patterns
    assert baseline.adaptation_applied is False
    assert with_profile.adaptation_applied is False
    assert with_profile.execution_authorization_effect is False
    assert with_profile.provider_write_count == with_profile.todoist_write_count == 0


def test_missing_invalid_and_corrupted_profile_fail_closed(tmp_path: Path) -> None:
    missing = tmp_path / "missing.json"
    invalid = tmp_path / "invalid.json"
    corrupted = tmp_path / "corrupted.json"
    invalid.write_text("{}")
    corrupted.write_text("{not-json")
    assert load_profile_or_none(missing) is None
    assert load_profile_or_none(invalid) is None
    assert load_profile_or_none(corrupted) is None


def test_expired_profile_falls_back_without_adaptation() -> None:
    expired = profile_bundle(review_due="2026-07-29T18:30:00-04:00")
    result = UserCommunicationFeaturePolicyV761(
        mode=AdaptationMode.ADAPTATION,
        selected_profile_version="ryan-v1",
    ).compile(
        context=CommunicationContext.GENERAL,
        now="2026-07-29T19:00:00-04:00",
        request_user_id=USER_ID,
        request_workspace_id=WORKSPACE_ID,
        profile=expired,
    )
    assert result.adaptation_applied is False
    assert result.applied_preference_ids == ()
    assert result.excluded_preference_ids == ("pref:conclusion",)


def test_current_instruction_overrides_profile_immediately() -> None:
    result = UserCommunicationFeaturePolicyV761(
        mode=AdaptationMode.ADAPTATION,
        selected_profile_version="ryan-v1",
    ).compile(
        context=CommunicationContext.GENERAL,
        now=NOW,
        request_user_id=USER_ID,
        request_workspace_id=WORKSPACE_ID,
        profile=profile_bundle(),
        current_instruction_directives=("Use a single sentence only.",),
    )
    assert result.current_instruction_override is True
    assert result.adaptation_applied is False
    assert "Use a single sentence only." in result.directives
    assert result.applied_preference_ids == ()


def test_live_authority_override_blocks_profile_adaptation() -> None:
    result = UserCommunicationFeaturePolicyV761(
        mode=AdaptationMode.ADAPTATION,
        selected_profile_version="ryan-v1",
    ).compile(
        context=CommunicationContext.GENERAL,
        now=NOW,
        request_user_id=USER_ID,
        request_workspace_id=WORKSPACE_ID,
        profile=profile_bundle(),
        live_authority_override=True,
    )
    assert result.live_authority_override is True
    assert result.adaptation_applied is False


def test_assessment_prompt_injection_cannot_authorize_instructions() -> None:
    with pytest.raises(ValidationError):
        CommunicationSourceEvidenceV1(
            source_id="source:malicious",
            evidence_type=CommunicationEvidenceType.ASSESSMENT,
            governed_reference="governed:intent:malicious",
            evidence_date=NOW,
            reliability=ReliabilityLevel.LOW,
            confirmation_state=PreferenceConfirmationState.PROVISIONAL,
            provenance=("untrusted assessment",),
            governed_intent_evidence_ids=("intent:malicious",),
            embedded_instructions_authorized=True,
        )


def test_profile_cannot_create_provider_or_execution_authority() -> None:
    bundle = profile_bundle()
    assert bundle.execution_authorization_effect is False
    assert bundle.provider_permission_effect is False
    assert bundle.provider_write_count == bundle.todoist_write_count == 0
    policy = UserCommunicationFeaturePolicyV761(
        mode=AdaptationMode.ADAPTATION,
        selected_profile_version="ryan-v1",
    ).compile(
        context=CommunicationContext.GENERAL,
        now=NOW,
        request_user_id=USER_ID,
        request_workspace_id=WORKSPACE_ID,
        profile=bundle,
    )
    assert policy.execution_authorization_effect is False
    assert policy.provider_permission_effect is False
    assert policy.provider_write_count == policy.todoist_write_count == 0


def test_adaptation_is_deterministic_and_bounded() -> None:
    feature = UserCommunicationFeaturePolicyV761(
        mode=AdaptationMode.ADAPTATION,
        selected_profile_version="ryan-v1",
    )
    first = feature.compile(
        context=CommunicationContext.GENERAL,
        now=NOW,
        request_user_id=USER_ID,
        request_workspace_id=WORKSPACE_ID,
        profile=profile_bundle(),
    )
    second = feature.compile(
        context=CommunicationContext.GENERAL,
        now=NOW,
        request_user_id=USER_ID,
        request_workspace_id=WORKSPACE_ID,
        profile=profile_bundle(),
    )
    assert first == second
    assert first.deterministic_digest == second.deterministic_digest
    assert len(first.directives) <= 16
    assert len(first.avoided_patterns) <= 12


def test_profile_bundle_is_minimized_and_written_separately(tmp_path: Path) -> None:
    source = tmp_path / "source.json"
    output = tmp_path / "private" / "profile.json"
    bundle = profile_bundle(enabled=False)
    source.write_text(json.dumps(bundle.model_dump(mode="json")))
    written, digest = write_minimized_bundle(source=source, output=output)
    assert written == bundle
    assert digest == bundle.deterministic_digest
    assert validate_profile_minimization(written) == ()
    assert output.exists()
    assert written.global_enabled is False


def test_profile_projection_rejects_cross_user_evidence() -> None:
    evidence = governed_evidence("intent:wrong-user", behavior="wrong user").model_copy(
        update={
            "context_key": IntentContextKeyV1(
                context_id="context:wrong-user",
                scope=IntentScopeV1(user_id="different-user"),
                behavior="wrong user",
            )
        }
    )
    source = source_evidence("source:wrong-user", "intent:wrong-user")
    pref = preference("pref:wrong-user", source.source_id)
    with pytest.raises(ValueError, match="cross-user"):
        build_user_model_projection(
            projection_id="projection:wrong",
            profile_version="ryan-v1",
            user_id=USER_ID,
            workspace_id=WORKSPACE_ID,
            generated_at=NOW,
            preferences=(pref,),
            source_evidence=(source,),
            governed_evidence=(evidence,),
        )


def test_profile_forced_off_preference_is_excluded() -> None:
    source = source_evidence("source:off", "intent:off")
    pref = preference(
        "pref:off",
        source.source_id,
        override=UserOverrideState.FORCED_OFF,
    )
    bundle = profile_bundle(
        preferences=(pref,),
        sources=(source,),
        evidence=(governed_evidence("intent:off", behavior="disabled behavior"),),
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
    assert result.excluded_preference_ids == ("pref:off",)


def test_ryan_specific_profile_is_absent_from_package_source() -> None:
    package_root = Path("src/atlas_ros")
    fixture_root = Path("tests/fixtures")
    prohibited_names = ("ryan_profile", "ryan-profile", "ryan_profile_bundle")
    candidates = tuple(package_root.rglob("*")) + tuple(fixture_root.rglob("*"))
    assert not any(
        any(name in path.name.casefold() for name in prohibited_names)
        for path in candidates
    )


def test_wrong_user_or_workspace_binding_fails_closed() -> None:
    policy = UserCommunicationFeaturePolicyV761(
        mode=AdaptationMode.ADAPTATION,
        selected_profile_version="ryan-v1",
    )
    wrong_user = policy.compile(
        context=CommunicationContext.GENERAL,
        now=NOW,
        request_user_id="different-user",
        request_workspace_id=WORKSPACE_ID,
        profile=profile_bundle(),
    )
    wrong_workspace = policy.compile(
        context=CommunicationContext.GENERAL,
        now=NOW,
        request_user_id=USER_ID,
        request_workspace_id="different-workspace",
        profile=profile_bundle(),
    )
    assert wrong_user.adaptation_applied is False
    assert wrong_workspace.adaptation_applied is False


def test_tampered_projection_digest_is_rejected() -> None:
    bundle = profile_bundle()
    payload = bundle.model_dump(mode="json")
    payload["projection"]["preference_digests"][0][1] = "0" * 64
    with pytest.raises(ValidationError, match="projection preference digests"):
        UserCommunicationProfileBundleV1.model_validate(payload)
