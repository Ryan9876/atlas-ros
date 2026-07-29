"""Typed user communication contracts for Atlas ROS v7.6.1."""
from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from atlas_ros.contracts.digests import sha256_digest

type Digest = str


class StrictContract(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class CommunicationEvidenceType(StrEnum):
    EXPLICIT_PREFERENCE = "explicit_preference"
    BEHAVIOR_CORRECTION = "behavior_correction"
    REPEATED_SELECTION = "repeated_selection"
    ASSESSMENT = "assessment"
    SYSTEM_INFERENCE = "system_inference"


class ReliabilityLevel(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class PreferenceConfirmationState(StrEnum):
    USER_CONFIRMED = "user_confirmed"
    ASSESSMENT_SUPPORTED = "assessment_supported"
    PROVISIONAL = "provisional"
    CONTRADICTED = "contradicted"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"


class SensitivityLevel(StrEnum):
    STANDARD = "standard"
    SENSITIVE = "sensitive"
    RESTRICTED = "restricted"


class UserOverrideState(StrEnum):
    DEFAULT = "default"
    FORCED_ON = "forced_on"
    FORCED_OFF = "forced_off"


class ContradictionState(StrEnum):
    NONE = "none"
    OPEN = "open"
    RESOLVED = "resolved"


class CommunicationContext(StrEnum):
    GENERAL = "general"
    DECISION_SUPPORT = "decision_support"
    CONFLICT_ACCOUNTABILITY = "conflict_accountability"
    LEADERSHIP_DELEGATION = "leadership_delegation"
    CAREER_SELF_ADVOCACY = "career_self_advocacy"
    WORKLOAD_COMMITMENTS = "workload_commitments"
    SENSITIVE_STRESSFUL = "sensitive_stressful"


class AdaptationMode(StrEnum):
    DISABLED = "disabled"
    INSPECTION = "inspection"
    ADAPTATION = "adaptation"


class DecisionConsequence(StrEnum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"


class DelegationMode(StrEnum):
    DELEGATE = "delegate"
    COACH_WITH_CHECKPOINTS = "coach_with_checkpoints"
    DIRECT_INSTRUCTION = "direct_instruction"
    RETAIN_OWNERSHIP = "retain_ownership"


class WorkloadDecision(StrEnum):
    ACCEPT = "accept"
    DELEGATE = "delegate"
    DECLINE = "decline"
    MINIMUM_SUCCESS = "minimum_success"


class CommunicationSourceEvidenceV1(StrictContract):
    source_id: str = Field(min_length=1)
    evidence_type: CommunicationEvidenceType
    source_document_digest: Digest | None = Field(default=None, min_length=64, max_length=64)
    governed_reference: str | None = None
    evidence_date: str = Field(min_length=1)
    reliability: ReliabilityLevel
    limitations: tuple[str, ...] = ()
    confirmation_state: PreferenceConfirmationState
    supersession_state: PreferenceConfirmationState | None = None
    sensitivity: SensitivityLevel = SensitivityLevel.STANDARD
    provenance: tuple[str, ...] = Field(min_length=1)
    governed_intent_evidence_ids: tuple[str, ...] = Field(min_length=1)
    assessment_content_untrusted: Literal[True] = True
    embedded_instructions_authorized: Literal[False] = False
    raw_content_retained: Literal[False] = False

    @model_validator(mode="after")
    def validate_source(self) -> CommunicationSourceEvidenceV1:
        _parse_timestamp(self.evidence_date)
        if not self.source_document_digest and not self.governed_reference:
            raise ValueError("source evidence requires a digest or governed reference")
        if (
            self.evidence_type is CommunicationEvidenceType.SYSTEM_INFERENCE
            and self.confirmation_state is not PreferenceConfirmationState.PROVISIONAL
        ):
            raise ValueError("system inference remains provisional until user confirmation")
        if tuple(sorted(set(self.governed_intent_evidence_ids))) != (
            self.governed_intent_evidence_ids
        ):
            raise ValueError("governed evidence identifiers must be unique and sorted")
        return self

    @property
    def deterministic_digest(self) -> Digest:
        return sha256_digest(self.model_dump(mode="json"))


class CommunicationPreferenceV1(StrictContract):
    preference_id: str = Field(min_length=1)
    practical_description: str = Field(min_length=1, max_length=300)
    applicable_contexts: tuple[CommunicationContext, ...] = Field(min_length=1)
    preferred_behaviors: tuple[str, ...] = ()
    avoided_behaviors: tuple[str, ...] = ()
    confidence: float = Field(ge=0.0, le=1.0)
    confirmation_state: PreferenceConfirmationState
    evidence_references: tuple[str, ...] = Field(min_length=1)
    created_at: str = Field(min_length=1)
    reviewed_at: str = Field(min_length=1)
    expires_at: str | None = None
    user_override_state: UserOverrideState = UserOverrideState.DEFAULT
    sensitivity: SensitivityLevel = SensitivityLevel.STANDARD
    contradiction_state: ContradictionState = ContradictionState.NONE
    authorization_effect: Literal[False] = False
    provider_permission_effect: Literal[False] = False

    @model_validator(mode="after")
    def validate_preference(self) -> CommunicationPreferenceV1:
        created = _parse_timestamp(self.created_at)
        reviewed = _parse_timestamp(self.reviewed_at)
        if created > reviewed:
            raise ValueError("preference review cannot precede creation")
        if self.expires_at is not None and _parse_timestamp(self.expires_at) < reviewed:
            raise ValueError("preference expiry cannot precede the review date")
        if not self.preferred_behaviors and not self.avoided_behaviors:
            raise ValueError("a preference requires a preferred or avoided behavior")
        if tuple(sorted(set(self.applicable_contexts))) != self.applicable_contexts:
            raise ValueError("applicable contexts must be unique and sorted")
        if tuple(sorted(set(self.evidence_references))) != self.evidence_references:
            raise ValueError("evidence references must be unique and sorted")
        if self.confirmation_state in {
            PreferenceConfirmationState.REJECTED,
            PreferenceConfirmationState.SUPERSEDED,
        } and self.user_override_state is UserOverrideState.FORCED_ON:
            raise ValueError("rejected or superseded preferences cannot be forced on")
        return self

    @property
    def deterministic_digest(self) -> Digest:
        return sha256_digest(self.model_dump(mode="json"))


class IntegratedUserModelProjectionV1(StrictContract):
    projection_id: str = Field(min_length=1)
    profile_version: str = Field(min_length=1)
    user_id: str = Field(min_length=1)
    workspace_id: str = Field(min_length=1)
    generated_at: str = Field(min_length=1)
    preference_ids: tuple[str, ...]
    preference_digests: tuple[tuple[str, Digest], ...]
    governed_evidence_ids: tuple[str, ...]
    source_evidence_digests: tuple[tuple[str, Digest], ...]
    contradiction_preference_ids: tuple[str, ...] = ()
    raw_assessment_content_retained: Literal[False] = False
    authorization_effect: Literal[False] = False
    provider_write_count: Literal[0] = 0
    todoist_write_count: Literal[0] = 0

    @model_validator(mode="after")
    def validate_projection(self) -> IntegratedUserModelProjectionV1:
        _parse_timestamp(self.generated_at)
        for field_name in (
            "preference_ids",
            "preference_digests",
            "governed_evidence_ids",
            "source_evidence_digests",
            "contradiction_preference_ids",
        ):
            value = getattr(self, field_name)
            if tuple(sorted(value)) != value:
                raise ValueError(f"{field_name} must be sorted")
        return self

    @property
    def deterministic_digest(self) -> Digest:
        return sha256_digest(self.model_dump(mode="json"))


class UserCommunicationProfileBundleV1(StrictContract):
    schema_version: Literal["1.0"] = "1.0"
    profile_version: str = Field(min_length=1)
    user_id: str = Field(min_length=1)
    workspace_id: str = Field(min_length=1)
    repository_binding: str = Field(min_length=1)
    generated_at: str = Field(min_length=1)
    review_due_at: str = Field(min_length=1)
    global_enabled: bool = False
    safe_baseline_fallback: Literal["v7.6.0"] = "v7.6.0"
    preferences: tuple[CommunicationPreferenceV1, ...]
    source_evidence: tuple[CommunicationSourceEvidenceV1, ...]
    projection: IntegratedUserModelProjectionV1
    context_disabled: tuple[CommunicationContext, ...] = ()
    preference_disabled: tuple[str, ...] = ()
    contains_raw_assessment_content: Literal[False] = False
    execution_authorization_effect: Literal[False] = False
    provider_permission_effect: Literal[False] = False
    provider_write_count: Literal[0] = 0
    todoist_write_count: Literal[0] = 0

    @model_validator(mode="after")
    def validate_bundle(self) -> UserCommunicationProfileBundleV1:
        generated = _parse_timestamp(self.generated_at)
        if _parse_timestamp(self.review_due_at) <= generated:
            raise ValueError("profile review date must be after generation")
        preference_ids = tuple(item.preference_id for item in self.preferences)
        source_ids = tuple(item.source_id for item in self.source_evidence)
        if tuple(sorted(preference_ids)) != preference_ids or len(set(preference_ids)) != len(
            preference_ids
        ):
            raise ValueError("profile preferences must be unique and sorted")
        if tuple(sorted(source_ids)) != source_ids or len(set(source_ids)) != len(source_ids):
            raise ValueError("source evidence must be unique and sorted")
        if self.projection.user_id != self.user_id:
            raise ValueError("profile and projection user bindings must match")
        if self.projection.workspace_id != self.workspace_id:
            raise ValueError("profile and projection workspace bindings must match")
        if self.projection.profile_version != self.profile_version:
            raise ValueError("profile and projection versions must match")
        if self.projection.preference_ids != preference_ids:
            raise ValueError("projection preference identifiers must match the bundle")
        expected_preference_digests = tuple(
            sorted((item.preference_id, item.deterministic_digest) for item in self.preferences)
        )
        if self.projection.preference_digests != expected_preference_digests:
            raise ValueError("projection preference digests must match the bundle")
        expected_source_digests = tuple(
            sorted((item.source_id, item.deterministic_digest) for item in self.source_evidence)
        )
        if self.projection.source_evidence_digests != expected_source_digests:
            raise ValueError("projection source-evidence digests must match the bundle")
        source_id_set = set(source_ids)
        for preference in self.preferences:
            if not set(preference.evidence_references).issubset(source_id_set):
                raise ValueError("preference evidence references must resolve in the bundle")
        expected_governed_ids = tuple(
            sorted(
                {
                    evidence_id
                    for source in self.source_evidence
                    for evidence_id in source.governed_intent_evidence_ids
                }
            )
        )
        if self.projection.governed_evidence_ids != expected_governed_ids:
            raise ValueError("projection governed-evidence identifiers must match the bundle")
        if tuple(sorted(set(self.context_disabled))) != self.context_disabled:
            raise ValueError("disabled contexts must be unique and sorted")
        if tuple(sorted(set(self.preference_disabled))) != self.preference_disabled:
            raise ValueError("disabled preferences must be unique and sorted")
        if not set(self.preference_disabled).issubset(preference_ids):
            raise ValueError("disabled preferences must resolve in the bundle")
        return self

    @property
    def deterministic_digest(self) -> Digest:
        return sha256_digest(self.model_dump(mode="json"))


class CompiledCommunicationPolicyV1(StrictContract):
    policy_version: Literal["1.0"] = "1.0"
    context: CommunicationContext
    profile_version: str | None
    profile_digest: Digest | None = Field(default=None, min_length=64, max_length=64)
    adaptation_mode: AdaptationMode
    adaptation_applied: bool
    current_instruction_override: bool = False
    live_authority_override: bool = False
    conclusion_first: bool = True
    separate_facts_assumptions_interpretations: bool = True
    explain_material_reasoning: bool = True
    present_meaningful_tradeoffs: bool = True
    recommend_preferred_option: bool = True
    challenge_assumptions_respectfully: bool = True
    state_uncertainty_directly: bool = True
    identify_diminishing_returns: bool = True
    concrete_next_action: bool = True
    preserve_required_clarification: bool = True
    sensitive_trace_redaction: bool = True
    directives: tuple[str, ...] = Field(max_length=16)
    avoided_patterns: tuple[str, ...] = Field(max_length=12)
    applied_preference_ids: tuple[str, ...] = ()
    excluded_preference_ids: tuple[str, ...] = ()
    execution_authorization_effect: Literal[False] = False
    provider_permission_effect: Literal[False] = False
    provider_write_count: Literal[0] = 0
    todoist_write_count: Literal[0] = 0

    @model_validator(mode="after")
    def validate_policy(self) -> CompiledCommunicationPolicyV1:
        for field_name in (
            "directives",
            "avoided_patterns",
            "applied_preference_ids",
            "excluded_preference_ids",
        ):
            value = getattr(self, field_name)
            if len(value) != len(set(value)):
                raise ValueError(f"{field_name} must be unique")
        return self

    @property
    def deterministic_digest(self) -> Digest:
        return sha256_digest(self.model_dump(mode="json"))


class AdaptationInspectionViewV1(StrictContract):
    policy_digest: Digest = Field(min_length=64, max_length=64)
    context: CommunicationContext
    adaptation_applied: bool
    reason_codes: tuple[str, ...]
    preference_identity_digests: tuple[Digest, ...]
    redacted: Literal[True] = True
    raw_profile_content_present: Literal[False] = False
    provider_write_count: Literal[0] = 0
    todoist_write_count: Literal[0] = 0


class DecisionSupportInputV1(StrictContract):
    consequence: DecisionConsequence
    reversible: bool
    missing_material_facts: bool
    additional_evidence_likely_to_change_outcome: bool
    delay_has_material_cost: bool = False
    explicit_deadline: str | None = None


class DecisionSupportResultV1(StrictContract):
    recommend_reasonable_default: bool
    clarification_required: bool
    diminishing_returns: bool
    manufactured_urgency: Literal[False] = False
    reason_codes: tuple[str, ...]
    next_action: str
    provider_write_count: Literal[0] = 0
    todoist_write_count: Literal[0] = 0


class ConflictAccountabilityInputV1(StrictContract):
    objective_facts_present: bool
    impact_present: bool
    expectation_explicit: bool
    required_action_explicit: bool
    consequence_explicit_when_needed: bool
    desired_outcome_present: bool
    likely_objections_considered: bool
    diplomatic_language_clear: bool


class ConflictAccountabilityResultV1(StrictContract):
    needs_strengthening: bool
    hidden_elements: tuple[str, ...]
    preserve_existing_diplomacy: bool
    aggression_increase_required: Literal[False] = False
    provider_write_count: Literal[0] = 0


class DelegationInputV1(StrictContract):
    capability: float = Field(ge=0.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0)
    consequence: DecisionConsequence
    outcome_clarity: float = Field(ge=0.0, le=1.0)
    checkpoints_available: bool
    accountability_belongs_to_other: bool
    support_becoming_rescue: bool = False


class DelegationResultV1(StrictContract):
    mode: DelegationMode
    checkpoints_required: bool
    accountability_gap: bool
    coaching_gap: bool
    rescue_risk: bool
    reason_codes: tuple[str, ...]
    provider_write_count: Literal[0] = 0


class CareerLanguageResultV1(StrictContract):
    original: str
    revised: str
    replacements: tuple[tuple[str, str], ...]
    unsupported_replacements_skipped: tuple[str, ...]
    team_credit_preserved: bool
    invented_metrics: Literal[False] = False


class WorkloadInputV1(StrictContract):
    ownership_is_mine: bool
    higher_priority_displaced: bool
    delegable: bool
    requester_retains_accountability: bool
    minimum_success_defined: bool
    impact_exceeds_effort: bool
    helping_reduces_other_accountability: bool


class WorkloadResultV1(StrictContract):
    decision: WorkloadDecision
    reason_codes: tuple[str, ...]
    minimum_success_required: bool
    displaced_priority_must_be_named: bool
    provider_write_count: Literal[0] = 0


class SensitiveDiscussionResultV1(StrictContract):
    acknowledgment: str
    practical_analysis_required: Literal[True] = True
    diagnostic_language_allowed: Literal[False] = False
    inferred_mental_state_allowed: Literal[False] = False


class PreferenceLearningInputV1(StrictContract):
    explicit_user_statement: bool = False
    user_behavior_correction: bool = False
    repeated_same_selection_count: int = Field(default=0, ge=0)
    assessment_interpretation_explicitly_confirmed: bool = False
    accepted_single_response: bool = False
    user_did_not_object: bool = False
    generic_assessment_description: bool = False
    inferred_emotion_or_motive: bool = False
    single_sensitive_conversation: bool = False
    third_party_description: bool = False


class PreferenceLearningDecisionV1(StrictContract):
    stable_preference_allowed: bool
    provisional_only: bool
    reason_codes: tuple[str, ...]
    provider_write_count: Literal[0] = 0
    todoist_write_count: Literal[0] = 0


def _parse_timestamp(value: str) -> datetime:
    normalized = value.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        raise ValueError("timestamps must include a timezone")
    return parsed.astimezone(UTC)
