"""Governed intent evidence and contextual familiarity contracts for Atlas ROS v7.6.0."""
from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from atlas_ros.contracts.digests import sha256_digest

type Digest = str


class StrictContract(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class EvidenceSourceKind(StrEnum):
    CURRENT_INSTRUCTION = "current_instruction"
    LIVE_AUTHORITY = "live_authority"
    CONFIRMED_INTERACTION = "confirmed_interaction"
    ATTRIBUTABLE_HISTORY = "attributable_history"


class FreshnessState(StrEnum):
    CURRENT = "current"
    STALE = "stale"
    EXPIRED = "expired"
    UNKNOWN = "unknown"


class UserControlState(StrEnum):
    ACTIVE = "active"
    CORRECTED = "corrected"
    RETIRED = "retired"
    FORGETTING_PENDING = "forgetting_pending"
    FORGOTTEN = "forgotten"


class EligibilityStatus(StrEnum):
    ELIGIBLE = "eligible"
    INELIGIBLE = "ineligible"
    CLARIFICATION_REQUIRED = "clarification_required"
    OVERRIDDEN = "overridden"


class FeatureMode(StrEnum):
    DISABLED = "disabled"
    INSPECTION = "inspection"
    INFERENCE = "inference"


class UserControlAction(StrEnum):
    CORRECTION = "correction"
    RETIREMENT = "retirement"
    FORGETTING_REQUEST = "forgetting_request"
    FORGETTING_VERIFIED = "forgetting_verified"


class IntentScopeV1(StrictContract):
    user_id: str = Field(min_length=1)
    domain: str | None = None
    project: str | None = None
    responsibility: str | None = None
    request_type: str | None = None
    sensitivity_domain: str | None = None

    def applies_to(self, other: IntentScopeV1) -> bool:
        if self.user_id != other.user_id:
            return False
        for name in ("domain", "project", "responsibility", "request_type", "sensitivity_domain"):
            required = getattr(self, name)
            actual = getattr(other, name)
            if required is not None and required != actual:
                return False
        return True

    @property
    def deterministic_digest(self) -> Digest:
        return sha256_digest(self.model_dump(mode="json"))


class IntentContextKeyV1(StrictContract):
    context_id: str = Field(min_length=1)
    scope: IntentScopeV1
    terminology: tuple[str, ...] = ()
    behavior: str | None = None

    @model_validator(mode="after")
    def normalize_terms(self) -> IntentContextKeyV1:
        normalized = tuple(
            sorted(
                {term.strip().casefold() for term in self.terminology if term.strip()}
            )
        )
        if normalized != self.terminology:
            object.__setattr__(self, "terminology", normalized)
        return self

    @property
    def deterministic_digest(self) -> Digest:
        return sha256_digest(self.model_dump(mode="json"))


class GovernedIntentEvidenceV1(StrictContract):
    schema_version: Literal["1.0"] = "1.0"
    evidence_id: str = Field(min_length=1)
    context_key: IntentContextKeyV1
    confirmed_interpretation: str = Field(min_length=1)
    represented_terminology: tuple[str, ...] = ()
    represented_behavior: str | None = None
    source_kind: EvidenceSourceKind
    source_reference: str = Field(min_length=1)
    source_digest: Digest = Field(min_length=64, max_length=64)
    confirmation_count: int = Field(ge=1)
    correction_count: int = Field(ge=0)
    contradiction_count: int = Field(ge=0)
    confidence: float = Field(ge=0.0, le=1.0)
    first_confirmed_at: str = Field(min_length=1)
    last_confirmed_at: str = Field(min_length=1)
    last_used_at: str | None = None
    freshness_state: FreshnessState = FreshnessState.UNKNOWN
    exceptions: tuple[str, ...] = ()
    inference_eligible: bool = False
    user_control_state: UserControlState = UserControlState.ACTIVE
    supersedes_evidence_id: str | None = None
    provenance: tuple[str, ...] = ()
    raw_sensitive_text_retained: Literal[False] = False

    @model_validator(mode="after")
    def enforce_governance(self) -> GovernedIntentEvidenceV1:
        _parse_timestamp(self.first_confirmed_at)
        last = _parse_timestamp(self.last_confirmed_at)
        if _parse_timestamp(self.first_confirmed_at) > last:
            raise ValueError("first confirmation cannot be after the last confirmation")
        if self.last_used_at is not None:
            _parse_timestamp(self.last_used_at)
        if self.user_control_state is not UserControlState.ACTIVE and self.inference_eligible:
            raise ValueError("non-active evidence cannot be inference eligible")
        if self.freshness_state is not FreshnessState.CURRENT and self.inference_eligible:
            raise ValueError("non-current evidence cannot be inference eligible")
        return self

    @property
    def deterministic_digest(self) -> Digest:
        return sha256_digest(self.model_dump(mode="json"))


class IntentConfirmationV1(StrictContract):
    confirmation_id: str = Field(min_length=1)
    evidence_id: str = Field(min_length=1)
    confirmed_interpretation: str = Field(min_length=1)
    confirmed_at: str = Field(min_length=1)
    source_reference: str = Field(min_length=1)
    source_digest: Digest = Field(min_length=64, max_length=64)

    @model_validator(mode="after")
    def validate_time(self) -> IntentConfirmationV1:
        _parse_timestamp(self.confirmed_at)
        return self

    @property
    def deterministic_digest(self) -> Digest:
        return sha256_digest(self.model_dump(mode="json"))


class IntentCorrectionV1(StrictContract):
    correction_id: str = Field(min_length=1)
    original_evidence_id: str = Field(min_length=1)
    original_evidence_digest: Digest = Field(min_length=64, max_length=64)
    corrected_evidence_id: str = Field(min_length=1)
    corrected_evidence_digest: Digest = Field(min_length=64, max_length=64)
    corrected_interpretation: str = Field(min_length=1)
    corrected_at: str = Field(min_length=1)
    source_reference: str = Field(min_length=1)

    @property
    def deterministic_digest(self) -> Digest:
        return sha256_digest(self.model_dump(mode="json"))


class IntentContradictionV1(StrictContract):
    contradiction_id: str = Field(min_length=1)
    evidence_id: str = Field(min_length=1)
    conflicting_interpretation: str = Field(min_length=1)
    detected_at: str = Field(min_length=1)
    source_reference: str = Field(min_length=1)
    resolved: bool = False
    resolution_reference: str | None = None

    @model_validator(mode="after")
    def validate_resolution(self) -> IntentContradictionV1:
        _parse_timestamp(self.detected_at)
        if self.resolved and not self.resolution_reference:
            raise ValueError("resolved contradictions require a resolution reference")
        return self

    @property
    def deterministic_digest(self) -> Digest:
        return sha256_digest(self.model_dump(mode="json"))


class IntentFreshnessPolicyV1(StrictContract):
    policy_id: str = Field(min_length=1)
    current_days: int = Field(ge=1)
    stale_days: int = Field(ge=1)
    max_inference_age_days: int = Field(ge=1)
    unknown_requires_clarification: bool = True
    stale_requires_clarification: bool = True
    contradiction_requires_clarification: bool = True

    @model_validator(mode="after")
    def ordered_windows(self) -> IntentFreshnessPolicyV1:
        if not self.current_days <= self.stale_days <= self.max_inference_age_days:
            raise ValueError("freshness windows must be monotonically increasing")
        return self

    @property
    def deterministic_digest(self) -> Digest:
        return sha256_digest(self.model_dump(mode="json"))


class IntentEligibilityDecisionV1(StrictContract):
    evidence_id: str = Field(min_length=1)
    status: EligibilityStatus
    reason_codes: tuple[str, ...]
    evidence_precedence: int = Field(ge=1, le=5)
    context_match: bool
    consequential: bool
    clarification_required: bool
    current_instruction_override: bool = False
    live_authority_override: bool = False
    provider_write_count: Literal[0] = 0
    todoist_write_count: Literal[0] = 0

    @property
    def deterministic_digest(self) -> Digest:
        return sha256_digest(self.model_dump(mode="json"))


class IntentMemoryIndexV1(StrictContract):
    schema_version: Literal["1.0"] = "1.0"
    snapshot_id: str = Field(min_length=1)
    snapshot_at: str = Field(min_length=1)
    request_context_digest: Digest = Field(min_length=64, max_length=64)
    active_evidence_ids: tuple[str, ...]
    excluded_evidence_ids: tuple[str, ...]
    evidence_digests: tuple[tuple[str, Digest], ...]
    eligibility_decisions: tuple[IntentEligibilityDecisionV1, ...]
    provider_write_count: Literal[0] = 0
    todoist_write_count: Literal[0] = 0

    @model_validator(mode="after")
    def deterministic_order(self) -> IntentMemoryIndexV1:
        if tuple(sorted(self.active_evidence_ids)) != self.active_evidence_ids:
            raise ValueError("active evidence identifiers must be sorted")
        if tuple(sorted(self.excluded_evidence_ids)) != self.excluded_evidence_ids:
            raise ValueError("excluded evidence identifiers must be sorted")
        if tuple(sorted(self.evidence_digests)) != self.evidence_digests:
            raise ValueError("evidence digests must be sorted")
        return self

    @property
    def deterministic_digest(self) -> Digest:
        return sha256_digest(self.model_dump(mode="json"))


class IntentInspectionViewV1(StrictContract):
    evidence_id: str
    interpreted_pattern: str
    evidence_source: str
    applicable_scope: IntentScopeV1
    confidence: float = Field(ge=0.0, le=1.0)
    freshness: FreshnessState
    contradictions: int = Field(ge=0)
    inference_eligibility: EligibilityStatus
    eligibility_reasons: tuple[str, ...]
    last_use: str | None
    user_control_state: UserControlState
    evidence_digest: Digest = Field(min_length=64, max_length=64)

    @property
    def deterministic_digest(self) -> Digest:
        return sha256_digest(self.model_dump(mode="json"))


class IntentForgettingTombstoneV1(StrictContract):
    tombstone_id: str = Field(min_length=1)
    evidence_identity_digest: Digest = Field(min_length=64, max_length=64)
    authorization_reference_digest: Digest = Field(min_length=64, max_length=64)
    provider_readback_digest: Digest = Field(min_length=64, max_length=64)
    retained_at: str = Field(min_length=1)
    contains_evidence_content: Literal[False] = False

    @property
    def deterministic_digest(self) -> Digest:
        return sha256_digest(self.model_dump(mode="json"))


class IntentUserControlReceiptV1(StrictContract):
    receipt_id: str = Field(min_length=1)
    action: UserControlAction
    evidence_id_digest: Digest = Field(min_length=64, max_length=64)
    original_evidence_digest: Digest = Field(min_length=64, max_length=64)
    resulting_evidence_digest: Digest | None = Field(default=None, min_length=64, max_length=64)
    tombstone_digest: Digest | None = Field(default=None, min_length=64, max_length=64)
    exact_authorization_reference: str | None = None
    applied: bool = False
    readback_verified: bool = False
    provider_write_count: int = Field(ge=0)
    todoist_write_count: Literal[0] = 0
    recorded_at: str = Field(min_length=1)

    @model_validator(mode="after")
    def enforce_control_receipt(self) -> IntentUserControlReceiptV1:
        _parse_timestamp(self.recorded_at)
        if self.action is UserControlAction.FORGETTING_VERIFIED:
            if (
                not self.exact_authorization_reference
                or not self.applied
                or not self.readback_verified
            ):
                raise ValueError(
                    "verified forgetting requires exact authorization and live readback"
                )
            if not self.tombstone_digest:
                raise ValueError("verified forgetting requires a content-free tombstone")
        if self.action is UserControlAction.FORGETTING_REQUEST and self.applied:
            raise ValueError("a forgetting request cannot itself claim deletion")
        return self

    @property
    def deterministic_digest(self) -> Digest:
        return sha256_digest(self.model_dump(mode="json"))


def evidence_precedence(source_kind: EvidenceSourceKind) -> int:
    return {
        EvidenceSourceKind.CURRENT_INSTRUCTION: 1,
        EvidenceSourceKind.LIVE_AUTHORITY: 2,
        EvidenceSourceKind.CONFIRMED_INTERACTION: 3,
        EvidenceSourceKind.ATTRIBUTABLE_HISTORY: 4,
    }[source_kind]


def freshness_state(
    *,
    last_confirmed_at: str,
    now: str,
    policy: IntentFreshnessPolicyV1,
) -> FreshnessState:
    age_days = (_parse_timestamp(now) - _parse_timestamp(last_confirmed_at)).total_seconds() / 86400
    if age_days < 0:
        return FreshnessState.UNKNOWN
    if age_days <= policy.current_days:
        return FreshnessState.CURRENT
    if age_days <= policy.stale_days:
        return FreshnessState.STALE
    return FreshnessState.EXPIRED


def decide_intent_eligibility(
    *,
    evidence: GovernedIntentEvidenceV1,
    request_context: IntentContextKeyV1,
    policy: IntentFreshnessPolicyV1,
    feature_mode: FeatureMode,
    now: str,
    consequential: bool = False,
    current_instruction_present: bool = False,
    live_authority_present: bool = False,
    scope_disabled: bool = False,
    evidence_disabled: bool = False,
) -> IntentEligibilityDecisionV1:
    precedence = evidence_precedence(evidence.source_kind)
    if current_instruction_present:
        return _decision(
            evidence,
            EligibilityStatus.OVERRIDDEN,
            ("current_instruction_overrides_memory",),
            precedence,
            False,
            consequential,
            False,
            current=True,
        )
    if live_authority_present:
        return _decision(
            evidence,
            EligibilityStatus.OVERRIDDEN,
            ("live_authority_overrides_memory",),
            precedence,
            False,
            consequential,
            False,
            authority=True,
        )
    context_match = evidence.context_key.scope.applies_to(request_context.scope)
    reasons: list[str] = []
    clarification = False
    if feature_mode is not FeatureMode.INFERENCE:
        reasons.append("inference_disabled")
    if scope_disabled:
        reasons.append("scope_disabled")
    if evidence_disabled:
        reasons.append("evidence_disabled")
    if not context_match:
        reasons.append("context_scope_mismatch")
        clarification = consequential
    if evidence.user_control_state is not UserControlState.ACTIVE:
        reasons.append(f"user_control_{evidence.user_control_state.value}")
    evaluated_freshness = freshness_state(
        last_confirmed_at=evidence.last_confirmed_at,
        now=now,
        policy=policy,
    )
    if evaluated_freshness is FreshnessState.UNKNOWN and policy.unknown_requires_clarification:
        reasons.append("freshness_unknown")
        clarification = True
    if (
        evaluated_freshness in (FreshnessState.STALE, FreshnessState.EXPIRED)
        and policy.stale_requires_clarification
    ):
        reasons.append(f"evidence_{evaluated_freshness.value}")
        clarification = True
    if (
        evidence.contradiction_count > evidence.correction_count
        and policy.contradiction_requires_clarification
    ):
        reasons.append("unresolved_contradiction")
        clarification = True
    if not evidence.inference_eligible:
        reasons.append("evidence_marked_ineligible")
    if evidence.confidence < 0.70:
        reasons.append("confidence_below_inference_floor")
        clarification = True
    if consequential and evidence.source_kind is EvidenceSourceKind.ATTRIBUTABLE_HISTORY:
        reasons.append("historical_evidence_cannot_control_consequential_classification")
        clarification = True
    if reasons:
        status = (
            EligibilityStatus.CLARIFICATION_REQUIRED
            if clarification
            else EligibilityStatus.INELIGIBLE
        )
        return _decision(
            evidence,
            status,
            tuple(sorted(set(reasons))),
            precedence,
            context_match,
            consequential,
            clarification,
        )
    return _decision(
        evidence,
        EligibilityStatus.ELIGIBLE,
        ("confirmed_current_scoped_evidence",),
        precedence,
        True,
        consequential,
        False,
    )


def build_intent_memory_index(
    *,
    snapshot_id: str,
    snapshot_at: str,
    request_context: IntentContextKeyV1,
    evidence_items: tuple[GovernedIntentEvidenceV1, ...],
    decisions: tuple[IntentEligibilityDecisionV1, ...],
) -> IntentMemoryIndexV1:
    by_id = {item.evidence_id: item for item in evidence_items}
    decision_by_id = {item.evidence_id: item for item in decisions}
    if set(by_id) != set(decision_by_id):
        raise ValueError("every evidence item requires exactly one eligibility decision")
    active = tuple(
        sorted(
            key
            for key, decision in decision_by_id.items()
            if decision.status is EligibilityStatus.ELIGIBLE
        )
    )
    excluded = tuple(sorted(set(by_id) - set(active)))
    return IntentMemoryIndexV1(
        snapshot_id=snapshot_id,
        snapshot_at=snapshot_at,
        request_context_digest=request_context.deterministic_digest,
        active_evidence_ids=active,
        excluded_evidence_ids=excluded,
        evidence_digests=tuple(
            sorted(
                (key, value.deterministic_digest)
                for key, value in by_id.items()
            )
        ),
        eligibility_decisions=tuple(sorted(decisions, key=lambda item: item.evidence_id)),
    )


def inspect_intent_evidence(
    evidence: GovernedIntentEvidenceV1,
    decision: IntentEligibilityDecisionV1,
) -> IntentInspectionViewV1:
    if evidence.evidence_id != decision.evidence_id:
        raise ValueError("inspection evidence and eligibility decision must match")
    return IntentInspectionViewV1(
        evidence_id=evidence.evidence_id,
        interpreted_pattern=evidence.confirmed_interpretation,
        evidence_source=evidence.source_reference,
        applicable_scope=evidence.context_key.scope,
        confidence=evidence.confidence,
        freshness=evidence.freshness_state,
        contradictions=evidence.contradiction_count,
        inference_eligibility=decision.status,
        eligibility_reasons=decision.reason_codes,
        last_use=evidence.last_used_at,
        user_control_state=evidence.user_control_state,
        evidence_digest=evidence.deterministic_digest,
    )


def correct_intent_evidence(
    *,
    evidence: GovernedIntentEvidenceV1,
    corrected_evidence_id: str,
    corrected_interpretation: str,
    corrected_at: str,
    source_reference: str,
    source_digest: Digest,
    correction_id: str,
    receipt_id: str,
) -> tuple[
    GovernedIntentEvidenceV1,
    GovernedIntentEvidenceV1,
    IntentCorrectionV1,
    IntentUserControlReceiptV1,
]:
    original = evidence.model_copy(update={
        "inference_eligible": False,
        "user_control_state": UserControlState.CORRECTED,
        "correction_count": evidence.correction_count + 1,
    })
    successor = GovernedIntentEvidenceV1(
        evidence_id=corrected_evidence_id,
        context_key=evidence.context_key,
        confirmed_interpretation=corrected_interpretation,
        represented_terminology=evidence.represented_terminology,
        represented_behavior=evidence.represented_behavior,
        source_kind=EvidenceSourceKind.CURRENT_INSTRUCTION,
        source_reference=source_reference,
        source_digest=source_digest,
        confirmation_count=1,
        correction_count=0,
        contradiction_count=0,
        confidence=1.0,
        first_confirmed_at=corrected_at,
        last_confirmed_at=corrected_at,
        freshness_state=FreshnessState.CURRENT,
        inference_eligible=True,
        supersedes_evidence_id=evidence.evidence_id,
        provenance=(evidence.deterministic_digest, source_reference),
    )
    correction = IntentCorrectionV1(
        correction_id=correction_id,
        original_evidence_id=evidence.evidence_id,
        original_evidence_digest=evidence.deterministic_digest,
        corrected_evidence_id=successor.evidence_id,
        corrected_evidence_digest=successor.deterministic_digest,
        corrected_interpretation=corrected_interpretation,
        corrected_at=corrected_at,
        source_reference=source_reference,
    )
    receipt = IntentUserControlReceiptV1(
        receipt_id=receipt_id,
        action=UserControlAction.CORRECTION,
        evidence_id_digest=sha256_digest(evidence.evidence_id),
        original_evidence_digest=evidence.deterministic_digest,
        resulting_evidence_digest=successor.deterministic_digest,
        applied=True,
        readback_verified=True,
        provider_write_count=0,
        recorded_at=corrected_at,
    )
    return original, successor, correction, receipt


def retire_intent_evidence(
    *,
    evidence: GovernedIntentEvidenceV1,
    receipt_id: str,
    recorded_at: str,
) -> tuple[GovernedIntentEvidenceV1, IntentUserControlReceiptV1]:
    retired = evidence.model_copy(
        update={
            "inference_eligible": False,
            "user_control_state": UserControlState.RETIRED,
        }
    )
    receipt = IntentUserControlReceiptV1(
        receipt_id=receipt_id,
        action=UserControlAction.RETIREMENT,
        evidence_id_digest=sha256_digest(evidence.evidence_id),
        original_evidence_digest=evidence.deterministic_digest,
        resulting_evidence_digest=retired.deterministic_digest,
        applied=True,
        readback_verified=True,
        provider_write_count=0,
        recorded_at=recorded_at,
    )
    return retired, receipt


def request_forgetting(
    *,
    evidence: GovernedIntentEvidenceV1,
    receipt_id: str,
    recorded_at: str,
) -> tuple[GovernedIntentEvidenceV1, IntentUserControlReceiptV1]:
    pending = evidence.model_copy(
        update={
            "inference_eligible": False,
            "user_control_state": UserControlState.FORGETTING_PENDING,
        }
    )
    receipt = IntentUserControlReceiptV1(
        receipt_id=receipt_id,
        action=UserControlAction.FORGETTING_REQUEST,
        evidence_id_digest=sha256_digest(evidence.evidence_id),
        original_evidence_digest=evidence.deterministic_digest,
        resulting_evidence_digest=pending.deterministic_digest,
        applied=False,
        readback_verified=False,
        provider_write_count=0,
        recorded_at=recorded_at,
    )
    return pending, receipt


def record_verified_forgetting(
    *,
    evidence: GovernedIntentEvidenceV1,
    tombstone_id: str,
    receipt_id: str,
    exact_authorization_reference: str,
    provider_readback_digest: Digest,
    recorded_at: str,
    provider_write_count: int,
) -> tuple[IntentForgettingTombstoneV1, IntentUserControlReceiptV1]:
    if not exact_authorization_reference.strip():
        raise ValueError("exact authorization is required for forgetting")
    if provider_write_count < 1:
        raise ValueError("verified forgetting must reflect an authorized provider mutation")
    tombstone = IntentForgettingTombstoneV1(
        tombstone_id=tombstone_id,
        evidence_identity_digest=sha256_digest(evidence.evidence_id),
        authorization_reference_digest=sha256_digest(exact_authorization_reference),
        provider_readback_digest=provider_readback_digest,
        retained_at=recorded_at,
    )
    receipt = IntentUserControlReceiptV1(
        receipt_id=receipt_id,
        action=UserControlAction.FORGETTING_VERIFIED,
        evidence_id_digest=sha256_digest(evidence.evidence_id),
        original_evidence_digest=evidence.deterministic_digest,
        tombstone_digest=tombstone.deterministic_digest,
        exact_authorization_reference=exact_authorization_reference,
        applied=True,
        readback_verified=True,
        provider_write_count=provider_write_count,
        recorded_at=recorded_at,
    )
    return tombstone, receipt


def _decision(
    evidence: GovernedIntentEvidenceV1,
    status: EligibilityStatus,
    reasons: tuple[str, ...],
    precedence: int,
    context_match: bool,
    consequential: bool,
    clarification: bool,
    *,
    current: bool = False,
    authority: bool = False,
) -> IntentEligibilityDecisionV1:
    return IntentEligibilityDecisionV1(
        evidence_id=evidence.evidence_id,
        status=status,
        reason_codes=reasons,
        evidence_precedence=precedence,
        context_match=context_match,
        consequential=consequential,
        clarification_required=clarification,
        current_instruction_override=current,
        live_authority_override=authority,
    )


def _parse_timestamp(value: str) -> datetime:
    normalized = value.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        raise ValueError("timestamps must include a timezone")
    return parsed.astimezone(UTC)
