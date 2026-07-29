from __future__ import annotations

from collections.abc import Iterable
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator


class RelationshipClassification(StrEnum):
    EXACT_DUPLICATE = "exact_duplicate"
    PARAPHRASED_DUPLICATE = "paraphrased_duplicate"
    RELATED_NON_EQUIVALENT = "related_but_non_equivalent"
    DISTINCT_OUTCOME = "materially_distinct_outcome"
    NEEDS_CLARIFICATION = "needs_clarification"


class EvidenceLevel(StrEnum):
    MINIMAL = "minimal"
    PARTIAL = "partial"
    STRONG = "strong"
    CONFIRMED_PATTERN = "confirmed_pattern"


class ClarificationStatus(StrEnum):
    NOT_REQUIRED = "not_required"
    REQUIRED = "required"
    ANSWERED = "answered"


class CompletionDimensionsV1(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    intended_outcome: str
    scope: str
    definition_of_done: str
    accountable_owner: str
    ryan_management_action: str
    execution_evidence: str
    completion_boundary: str

    def materially_equivalent(self, other: CompletionDimensionsV1) -> bool:
        return all(
            _normalize(getattr(self, field)) == _normalize(getattr(other, field))
            for field in self.__class__.model_fields
        )


class ContextFamiliarityV1(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    user: float = Field(ge=0, le=1)
    domain: float = Field(ge=0, le=1)
    project: float = Field(ge=0, le=1)
    terminology: float = Field(ge=0, le=1)
    evidence_recency: float = Field(ge=0, le=1)
    interpretation_consistency: float = Field(ge=0, le=1)

    @property
    def contextual_score(self) -> float:
        return (
            self.user
            + self.domain
            + self.project
            + self.terminology
            + self.evidence_recency
            + self.interpretation_consistency
        ) / 6.0


class ConsequenceAssessmentV1(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    security: bool = False
    cost: bool = False
    compliance: bool = False
    architecture: bool = False
    production: bool = False
    vendor: bool = False
    external_commitment: bool = False
    reversible: bool = True

    @property
    def consequential(self) -> bool:
        return any(
            (
                self.security,
                self.cost,
                self.compliance,
                self.architecture,
                self.production,
                self.vendor,
                self.external_commitment,
            )
        )


class RelatedRecordV1(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    record_id: str
    title: str
    url: str | None = None
    completion: CompletionDimensionsV1 | None = None


class IntentEvidenceV1(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    evidence_id: str
    context_key: str
    interpretation: str
    confirmed: bool
    corrected_by_user: bool = False
    stale: bool = False
    contradictory: bool = False


class ClarificationDecisionV1(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    original_capture: str
    related_record_ids: tuple[str, ...]
    candidate_interpretations: tuple[str, ...]
    material_distinction: str
    evidence_level: EvidenceLevel
    familiarity: ContextFamiliarityV1
    consequence: ConsequenceAssessmentV1
    relationship: RelationshipClassification
    clarification_status: ClarificationStatus
    clarification_question: str | None
    clarification_reason: str | None
    preserve_capture: bool = True
    todoist_write_allowed: bool = False
    provider_writes: int = 0

    @model_validator(mode="after")
    def enforce_execution_boundary(self) -> ClarificationDecisionV1:
        if self.clarification_status == ClarificationStatus.REQUIRED:
            if not self.clarification_question:
                raise ValueError("required clarification must include a focused question")
            if self.todoist_write_allowed:
                raise ValueError("Todoist writes are prohibited while clarification is required")
        if self.provider_writes != 0:
            raise ValueError("planning and clarification decisions must remain provider-write free")
        return self


def decide_relationship(
    *,
    capture: str,
    proposed_completion: CompletionDimensionsV1 | None,
    related_records: Iterable[RelatedRecordV1],
    familiarity: ContextFamiliarityV1,
    consequence: ConsequenceAssessmentV1,
    evidence: Iterable[IntentEvidenceV1] = (),
) -> ClarificationDecisionV1:
    records = tuple(related_records)
    evidence_items = tuple(evidence)
    confirmed = tuple(
        item
        for item in evidence_items
        if item.confirmed and not item.stale and not item.contradictory
    )
    corrected = tuple(item for item in confirmed if item.corrected_by_user)
    evidence_level = _evidence_level(
        familiarity.contextual_score,
        len(confirmed),
        len(corrected),
    )

    equivalent = tuple(
        record
        for record in records
        if proposed_completion is not None
        and record.completion is not None
        and proposed_completion.materially_equivalent(record.completion)
    )
    if equivalent:
        relationship = (
            RelationshipClassification.EXACT_DUPLICATE
            if _normalize(capture) == _normalize(equivalent[0].title)
            else RelationshipClassification.PARAPHRASED_DUPLICATE
        )
        return ClarificationDecisionV1(
            original_capture=capture,
            related_record_ids=tuple(record.record_id for record in records),
            candidate_interpretations=(),
            material_distinction="All material completion dimensions are equivalent.",
            evidence_level=evidence_level,
            familiarity=familiarity,
            consequence=consequence,
            relationship=relationship,
            clarification_status=ClarificationStatus.NOT_REQUIRED,
            clarification_question=None,
            clarification_reason=None,
        )

    candidate_interpretations = _candidate_interpretations(capture)
    completion_boundary_unresolved = proposed_completion is None
    uncertainty_is_material = (
        completion_boundary_unresolved
        or consequence.consequential
        or not consequence.reversible
        or familiarity.contextual_score < 0.72
        or (completion_boundary_unresolved and len(candidate_interpretations) > 1)
    )
    if records and uncertainty_is_material:
        context = ", ".join(record.title for record in records[:3])
        question = (
            f"I found related work for {context}. Is '{capture}' a separate outcome "
            "with its own completion boundary, or should it describe the existing "
            "work collectively?"
        )
        return ClarificationDecisionV1(
            original_capture=capture,
            related_record_ids=tuple(record.record_id for record in records),
            candidate_interpretations=candidate_interpretations,
            material_distinction=(
                "Shared subject matter does not establish equivalent intended outcome, "
                "scope, Definition of Done, ownership, evidence, or completion boundary."
            ),
            evidence_level=evidence_level,
            familiarity=familiarity,
            consequence=consequence,
            relationship=RelationshipClassification.NEEDS_CLARIFICATION,
            clarification_status=ClarificationStatus.REQUIRED,
            clarification_question=question,
            clarification_reason=(
                "Completing the existing record may not necessarily satisfy the new capture."
            ),
        )

    relationship = (
        RelationshipClassification.RELATED_NON_EQUIVALENT
        if records
        else RelationshipClassification.DISTINCT_OUTCOME
    )
    return ClarificationDecisionV1(
        original_capture=capture,
        related_record_ids=tuple(record.record_id for record in records),
        candidate_interpretations=candidate_interpretations,
        material_distinction=(
            "The proposed completion dimensions are not equivalent to related records."
        ),
        evidence_level=evidence_level,
        familiarity=familiarity,
        consequence=consequence,
        relationship=relationship,
        clarification_status=ClarificationStatus.NOT_REQUIRED,
        clarification_question=None,
        clarification_reason=None,
    )


def _evidence_level(score: float, confirmed: int, corrected: int) -> EvidenceLevel:
    if corrected >= 2 and confirmed >= 4 and score >= 0.85:
        return EvidenceLevel.CONFIRMED_PATTERN
    if confirmed >= 2 and score >= 0.70:
        return EvidenceLevel.STRONG
    if confirmed >= 1 or score >= 0.45:
        return EvidenceLevel.PARTIAL
    return EvidenceLevel.MINIMAL


def _candidate_interpretations(capture: str) -> tuple[str, ...]:
    lowered = capture.casefold()
    if "centrally manage" in lowered and "device" in lowered:
        return (
            "centralized configuration management",
            "lifecycle management",
            "access management",
            "operational control",
            "management-platform evaluation",
            "automation",
            "centralized monitoring beyond inventory discovery",
        )
    return ("distinct deliverable", "umbrella objective", "restatement of related work")


def _normalize(value: str) -> str:
    return " ".join(value.casefold().split())
