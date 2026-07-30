"""Deterministic clarification-analysis contracts for Atlas ROS v8.1."""
from __future__ import annotations

from enum import StrEnum
from typing import Any, Literal

from pydantic import Field, model_validator

from atlas_ros.contracts.advisory_v1 import ConfidenceAssessment

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


class InterpretationCandidateV1(StrictModel):
    normalized_instruction: str
    rationale: str
    confidence: float = Field(ge=0.0, le=1.0)
    material: bool = True
    unsupported_assumptions: tuple[str, ...] = ()


class ClarificationAnalysisV1(DigestBoundModel):
    """Provider-free analysis that can request clarification but cannot authorize work."""

    digest_field = "analysis_digest"

    contract_id: Literal["atlas.clarification-analysis"] = "atlas.clarification-analysis"
    schema_version: Literal["1.0"] = "1.0"
    original_instruction: str
    stable_intent: tuple[str, ...]
    ambiguity_category: AmbiguityCategory
    ambiguous_span: str | None = None
    context_sources_checked: tuple[str, ...] = ()
    candidates: tuple[InterpretationCandidateV1, ...] = ()
    leading_interpretation: str | None = None
    clarification_required: bool
    question_mode: ClarificationQuestionMode | None = None
    clarification_question: str | None = None
    continue_unrelated_work: bool = True
    downstream_execution_blocked: bool = True
    provider_write_count: Literal[0] = 0
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
        if not all(item.strip() for item in self.stable_intent):
            raise ValueError("stable intent entries must be non-empty")
        if self.leading_interpretation is not None:
            if not self.candidates:
                raise ValueError("leading interpretation requires candidates")
            if self.leading_interpretation != self.candidates[0].normalized_instruction:
                raise ValueError("leading interpretation must equal the first ranked candidate")
        if self.clarification_required:
            if self.question_mode is None or not self.clarification_question:
                raise ValueError("clarification-required analysis must include a question")
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
    provider_write_count: Literal[0] = 0
    resolution_digest: str = Field(pattern=r"^[0-9a-f]{64}$")

    @classmethod
    def create(cls, **values: Any) -> ClarificationResolutionV1:
        return cls(resolution_digest=cls.compute_digest(values), **values)

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
        if not self.verify_digest():
            raise ValueError("clarification resolution digest mismatch")
        return self
