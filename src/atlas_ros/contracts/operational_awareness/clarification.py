"""Deterministic clarification contracts for Atlas ROS v8.1."""
from __future__ import annotations

from enum import StrEnum
from typing import Any, Literal

from pydantic import Field, model_validator

from atlas_ros.contracts.advisory_v1 import ConfidenceAssessment
from atlas_ros.contracts.digests import sha256_digest

from .base import DigestBoundModel, StrictModel


class AmbiguityCategory(StrEnum):
    NONE = "none"
    TRANSCRIPTION_ERROR = "suspected_transcription_error"
    CONNECTOR_ERROR = "incorrect_relationship_or_connector_word"
    MISSING_TARGET = "missing_target"
    MISSING_ENTITY = "missing_project_or_application_name"
    POSSIBLE_PROPER_NOUN = "unrecognized_possible_proper_noun"
    MULTIPLE_TARGETS = "multiple_plausible_targets"
    MISSING_OWNER = "missing_ownership"
    MISSING_OUTCOME = "missing_expected_outcome"
    MISSING_COMPLETION_CRITERIA = "missing_completion_criteria"
    CONFLICTING_DATES = "conflicting_dates"
    CONFLICTING_PRIORITIES = "conflicting_priorities"
    AMBIGUOUS_PRONOUN = "ambiguous_pronoun"
    AMBIGUOUS_DELEGATION = "ambiguous_delegation"
    ACTION_VERSUS_PROJECT = "ambiguous_action_versus_project"
    REQUEST_VERSUS_NOTE = "ambiguous_request_versus_informational_note"


class ClarificationQuestionMode(StrEnum):
    CONFIRMATORY = "confirmatory"
    BOUNDED_CHOICE = "bounded_choice"
    INFORMATION_SEEKING = "information_seeking"


class ClarificationBatchDisposition(StrEnum):
    COMPLETED_BEFORE_INTERRUPTION = "completed_before_interruption"
    PAUSED_FOR_CLARIFICATION = "paused_for_clarification"
    ELIGIBLE_AFTER_INTERRUPTION = "eligible_after_interruption"
    CLEAR_NO_INTERRUPTION = "clear_no_interruption"


class ClarificationReplayDisposition(StrEnum):
    APPLIED = "applied"
    DUPLICATE_IGNORED = "duplicate_ignored"


class ClarificationContextV1(StrictModel):
    """Bounded, authoritative context supplied to clarification analysis."""

    authoritative_snapshot_digest: str | None = Field(
        default=None, pattern=r"^[0-9a-f]{64}$"
    )
    source_refs: tuple[str, ...] = ()
    known_entities: tuple[str, ...] = ()
    context_terms: tuple[str, ...] = ()
    candidate_targets: tuple[str, ...] = ()
    related_record_ids: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_context(self) -> ClarificationContextV1:
        values = (
            *self.source_refs,
            *self.known_entities,
            *self.context_terms,
            *self.candidate_targets,
            *self.related_record_ids,
        )
        if not all(item.strip() for item in values):
            raise ValueError("clarification context entries must be non-empty")
        return self


class InterpretationCandidateV1(StrictModel):
    normalized_instruction: str
    rationale: str
    confidence: float = Field(ge=0.0, le=1.0)
    material: bool = True
    unsupported_assumptions: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_candidate(self) -> InterpretationCandidateV1:
        if not self.normalized_instruction.strip() or not self.rationale.strip():
            raise ValueError("interpretation candidates require content and rationale")
        return self


class ClarificationAnalysisV1(DigestBoundModel):
    """Provider-free analysis that can request clarification but cannot authorize work."""

    digest_field = "analysis_digest"

    contract_id: Literal["atlas.clarification-analysis"] = "atlas.clarification-analysis"
    schema_version: Literal["1.0"] = "1.0"
    original_instruction: str
    stable_intent: tuple[str, ...]
    ambiguity_category: AmbiguityCategory
    ambiguous_span: str | None = None
    preserved_entities: tuple[str, ...] = ()
    context_sources_checked: tuple[str, ...] = ()
    authoritative_context_digest: str | None = Field(
        default=None, pattern=r"^[0-9a-f]{64}$"
    )
    evidence: tuple[str, ...] = ()
    candidates: tuple[InterpretationCandidateV1, ...] = ()
    leading_interpretation: str | None = None
    clarification_required: bool
    question_mode: ClarificationQuestionMode | None = None
    clarification_question: str | None = None
    question_basis: str | None = None
    continue_unrelated_work: bool = True
    downstream_execution_blocked: bool = True
    routing_allowed: Literal[False] = False
    execution_authorized: Literal[False] = False
    provider_write_count: Literal[0] = 0
    todoist_write_count: Literal[0] = 0
    confidence: ConfidenceAssessment
    blockers: tuple[str, ...] = ()
    analysis_digest: str = Field(pattern=r"^[0-9a-f]{64}$")

    @classmethod
    def create(cls, **values: Any) -> ClarificationAnalysisV1:
        return cls(analysis_digest=cls.compute_digest(values), **values)

    @model_validator(mode="after")
    def validate_analysis(self) -> ClarificationAnalysisV1:
        if not self.original_instruction.strip():
            raise ValueError("clarification analysis requires original instruction")
        if not self.stable_intent or not all(item.strip() for item in self.stable_intent):
            raise ValueError("clarification analysis requires stable intent")
        if not all(item.strip() for item in self.preserved_entities):
            raise ValueError("preserved entities must be non-empty")
        if self.leading_interpretation is not None:
            if not self.candidates:
                raise ValueError("leading interpretation requires candidates")
            if self.leading_interpretation != self.candidates[0].normalized_instruction:
                raise ValueError("leading interpretation must equal the first ranked candidate")
        if self.clarification_required:
            if self.question_mode is None or not self.clarification_question:
                raise ValueError("clarification-required analysis must include a question")
            if not self.question_basis:
                raise ValueError("clarification-required analysis must explain its question")
            if not self.downstream_execution_blocked or not self.blockers:
                raise ValueError("clarification-required analysis must fail closed")
        else:
            if self.question_mode is not None or self.clarification_question is not None:
                raise ValueError("resolved analysis must not include a clarification question")
            if self.downstream_execution_blocked or self.blockers:
                raise ValueError("resolved analysis must not remain blocked")
        if not self.verify_digest():
            raise ValueError("clarification analysis digest mismatch")
        return self


class ClarificationResolutionV1(DigestBoundModel):
    """Traceable binding of one user answer to one clarification analysis."""

    digest_field = "resolution_digest"

    contract_id: Literal["atlas.clarification-resolution"] = "atlas.clarification-resolution"
    schema_version: Literal["1.0"] = "1.0"
    capture_id: str
    correlation_id: str
    analysis_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    original_instruction: str
    clarification_question: str
    user_response: str
    normalized_instruction: str
    ambiguity_category: AmbiguityCategory
    resolved_at: str | None = None
    idempotency_identity: str
    routing_allowed: Literal[False] = False
    execution_authorized: Literal[False] = False
    provider_write_count: Literal[0] = 0
    todoist_write_count: Literal[0] = 0
    resolution_digest: str = Field(pattern=r"^[0-9a-f]{64}$")

    @classmethod
    def create(cls, **values: Any) -> ClarificationResolutionV1:
        normalized = " ".join(str(values["normalized_instruction"]).strip().split())
        identity_digest = sha256_digest(
            {
                "capture_id": str(values["capture_id"]).strip(),
                "correlation_id": str(values["correlation_id"]).strip(),
                "analysis_digest": str(values["analysis_digest"]),
                "normalized_instruction": normalized.casefold(),
            }
        )
        payload = dict(values)
        payload["normalized_instruction"] = normalized
        payload["idempotency_identity"] = f"clarification-resolution:{identity_digest}"
        return cls(resolution_digest=cls.compute_digest(payload), **payload)

    @model_validator(mode="after")
    def validate_resolution(self) -> ClarificationResolutionV1:
        required = (
            self.capture_id,
            self.correlation_id,
            self.original_instruction,
            self.clarification_question,
            self.user_response,
            self.normalized_instruction,
        )
        if not all(item.strip() for item in required):
            raise ValueError("clarification resolution fields must be non-empty")
        identity_digest = sha256_digest(
            {
                "capture_id": self.capture_id,
                "correlation_id": self.correlation_id,
                "analysis_digest": self.analysis_digest,
                "normalized_instruction": self.normalized_instruction.casefold(),
            }
        )
        if self.idempotency_identity != f"clarification-resolution:{identity_digest}":
            raise ValueError("clarification resolution idempotency identity mismatch")
        if not self.verify_digest():
            raise ValueError("clarification resolution digest mismatch")
        return self


class ClarificationCompatibilityBindingV1(DigestBoundModel):
    """Binding to the accepted v7.5.2 clarification decision authority."""

    digest_field = "binding_digest"

    contract_id: Literal["atlas.clarification-compatibility-binding"] = (
        "atlas.clarification-compatibility-binding"
    )
    schema_version: Literal["1.0"] = "1.0"
    analysis_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    predecessor_decision_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    predecessor_relationship: str
    predecessor_status: str
    routing_allowed: Literal[False] = False
    execution_authorized: Literal[False] = False
    provider_write_count: Literal[0] = 0
    todoist_write_count: Literal[0] = 0
    binding_digest: str = Field(pattern=r"^[0-9a-f]{64}$")

    @classmethod
    def create(cls, **values: Any) -> ClarificationCompatibilityBindingV1:
        return cls(binding_digest=cls.compute_digest(values), **values)

    @model_validator(mode="after")
    def validate_binding(self) -> ClarificationCompatibilityBindingV1:
        if not self.predecessor_relationship.strip() or not self.predecessor_status.strip():
            raise ValueError("predecessor binding requires relationship and status")
        if not self.verify_digest():
            raise ValueError("clarification compatibility binding digest mismatch")
        return self


class ClarificationBatchItemResultV1(StrictModel):
    capture_id: str
    correlation_id: str
    position: int = Field(ge=1)
    disposition: ClarificationBatchDisposition
    analysis_digest: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    clarification_question: str | None = None

    @model_validator(mode="after")
    def validate_item(self) -> ClarificationBatchItemResultV1:
        if not self.capture_id.strip() or not self.correlation_id.strip():
            raise ValueError("batch item requires capture and correlation identity")
        paused = self.disposition == ClarificationBatchDisposition.PAUSED_FOR_CLARIFICATION
        if paused and (not self.analysis_digest or not self.clarification_question):
            raise ValueError("paused item requires analysis and question")
        if not paused and self.clarification_question is not None:
            raise ValueError("only a paused item may carry a question")
        return self


class ClarificationBatchPlanV1(DigestBoundModel):
    """Next-safe-interruption plan for one attended inbox batch."""

    digest_field = "batch_plan_digest"

    contract_id: Literal["atlas.clarification-batch-plan"] = (
        "atlas.clarification-batch-plan"
    )
    schema_version: Literal["1.0"] = "1.0"
    item_results: tuple[ClarificationBatchItemResultV1, ...]
    clarification_capture_id: str | None = None
    clarification_question: str | None = None
    interruption_position: int | None = Field(default=None, ge=1)
    interrupt_before_next_item: bool = False
    processed_before_interruption: tuple[str, ...] = ()
    eligible_after_interruption: tuple[str, ...] = ()
    paused_capture_ids: tuple[str, ...] = ()
    routing_allowed: Literal[False] = False
    execution_authorized: Literal[False] = False
    provider_write_count: Literal[0] = 0
    todoist_write_count: Literal[0] = 0
    batch_plan_digest: str = Field(pattern=r"^[0-9a-f]{64}$")

    @classmethod
    def create(cls, **values: Any) -> ClarificationBatchPlanV1:
        return cls(batch_plan_digest=cls.compute_digest(values), **values)

    @model_validator(mode="after")
    def validate_plan(self) -> ClarificationBatchPlanV1:
        capture_ids = tuple(item.capture_id for item in self.item_results)
        if len(capture_ids) != len(set(capture_ids)):
            raise ValueError("batch plan capture identities must be unique")
        if self.clarification_capture_id is None:
            if (
                self.clarification_question is not None
                or self.interruption_position is not None
                or self.paused_capture_ids
                or self.interrupt_before_next_item
            ):
                raise ValueError("clear batch must not contain interruption state")
        else:
            if (
                not self.clarification_question
                or self.interruption_position is None
                or self.paused_capture_ids != (self.clarification_capture_id,)
                or not self.interrupt_before_next_item
            ):
                raise ValueError("clarification batch must define one immediate interruption")
        if not self.verify_digest():
            raise ValueError("clarification batch plan digest mismatch")
        return self


class ClarificationResumptionReceiptV1(DigestBoundModel):
    """Exact-once, provider-free receipt for resuming one clarified item."""

    digest_field = "receipt_digest"

    contract_id: Literal["atlas.clarification-resumption-receipt"] = (
        "atlas.clarification-resumption-receipt"
    )
    schema_version: Literal["1.0"] = "1.0"
    capture_id: str
    correlation_id: str
    analysis_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    resolution_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    idempotency_identity: str
    replay_disposition: ClarificationReplayDisposition
    normalized_instruction: str
    follow_up_analysis_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    remaining_clarification_required: bool
    reclassification_required: bool
    routing_allowed: Literal[False] = False
    execution_authorized: Literal[False] = False
    provider_write_count: Literal[0] = 0
    todoist_write_count: Literal[0] = 0
    receipt_digest: str = Field(pattern=r"^[0-9a-f]{64}$")

    @classmethod
    def create(cls, **values: Any) -> ClarificationResumptionReceiptV1:
        return cls(receipt_digest=cls.compute_digest(values), **values)

    @model_validator(mode="after")
    def validate_receipt(self) -> ClarificationResumptionReceiptV1:
        if not all(
            item.strip()
            for item in (
                self.capture_id,
                self.correlation_id,
                self.idempotency_identity,
                self.normalized_instruction,
            )
        ):
            raise ValueError("resumption receipt requires exact identities")
        if self.replay_disposition == ClarificationReplayDisposition.DUPLICATE_IGNORED:
            if self.reclassification_required:
                raise ValueError("duplicate resolution must not re-run classification")
        elif not self.reclassification_required:
            raise ValueError("first resolution must require reclassification")
        if not self.verify_digest():
            raise ValueError("clarification resumption receipt digest mismatch")
        return self
