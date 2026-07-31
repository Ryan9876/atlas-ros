"""Canonical structural compatibility with accepted v7.5.2 clarification decisions."""
from __future__ import annotations

from enum import StrEnum

from pydantic import Field, model_validator

from atlas_ros.contracts.operational_awareness.base import StrictModel


class RelationshipClassificationV752(StrEnum):
    EXACT_DUPLICATE = "exact_duplicate"
    PARAPHRASED_DUPLICATE = "paraphrased_duplicate"
    RELATED_NON_EQUIVALENT = "related_but_non_equivalent"
    DISTINCT_OUTCOME = "materially_distinct_outcome"
    NEEDS_CLARIFICATION = "needs_clarification"


class EvidenceLevelV752(StrEnum):
    MINIMAL = "minimal"
    PARTIAL = "partial"
    STRONG = "strong"
    CONFIRMED_PATTERN = "confirmed_pattern"


class ClarificationStatusV752(StrEnum):
    NOT_REQUIRED = "not_required"
    REQUIRED = "required"
    ANSWERED = "answered"


class ContextFamiliarityV752(StrictModel):
    user: float = Field(ge=0, le=1)
    domain: float = Field(ge=0, le=1)
    project: float = Field(ge=0, le=1)
    terminology: float = Field(ge=0, le=1)
    evidence_recency: float = Field(ge=0, le=1)
    interpretation_consistency: float = Field(ge=0, le=1)


class ConsequenceAssessmentV752(StrictModel):
    security: bool = False
    cost: bool = False
    compliance: bool = False
    architecture: bool = False
    production: bool = False
    vendor: bool = False
    external_commitment: bool = False
    reversible: bool = True


class ClarificationDecisionV752Compatibility(StrictModel):
    """Exact field-compatible payload for accepted v7.5.2 ClarificationDecisionV1."""

    original_capture: str
    related_record_ids: tuple[str, ...]
    candidate_interpretations: tuple[str, ...]
    material_distinction: str
    evidence_level: EvidenceLevelV752
    familiarity: ContextFamiliarityV752
    consequence: ConsequenceAssessmentV752
    relationship: RelationshipClassificationV752
    clarification_status: ClarificationStatusV752
    clarification_question: str | None
    clarification_reason: str | None
    preserve_capture: bool = True
    todoist_write_allowed: bool = False
    provider_writes: int = 0

    @model_validator(mode="after")
    def enforce_execution_boundary(self) -> ClarificationDecisionV752Compatibility:
        if self.clarification_status == ClarificationStatusV752.REQUIRED:
            if not self.clarification_question:
                raise ValueError("required clarification must include a focused question")
            if self.todoist_write_allowed:
                raise ValueError("Todoist writes are prohibited while clarification is required")
        if self.provider_writes != 0:
            raise ValueError("clarification compatibility must remain provider-write free")
        return self
