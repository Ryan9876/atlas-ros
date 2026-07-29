"""Execution context-pack and resumption-memory contracts."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import Field, model_validator

from atlas_ros.contracts.advisory_v1 import ConfidenceAssessment

from .base import DigestBoundModel, EffectiveWorkState
from .evidence import FreshnessAssessmentV1
from .records import OperationalRecordRefV1


class ResumptionPointV1(DigestBoundModel):
    digest_field = "resumption_digest"

    contract_id: Literal["atlas.resumption-point"] = "atlas.resumption-point"
    schema_version: Literal["1.0"] = "1.0"
    where_execution_stopped: str | None = None
    last_confirmed_action: str | None = None
    conclusion_reached: str | None = None
    unresolved_question: str | None = None
    next_concrete_action: str | None = None
    source_evidence: tuple[str, ...] = ()
    confidence: ConfidenceAssessment
    generated_time: str
    unknown_reason: str | None = None
    minimum_verification_required: str | None = None
    resumption_digest: str = Field(pattern=r"^[0-9a-f]{64}$")

    @classmethod
    def create(cls, **values: Any) -> ResumptionPointV1:
        return cls(resumption_digest=cls.compute_digest(values), **values)

    @model_validator(mode="after")
    def validate_point(self) -> ResumptionPointV1:
        if self.where_execution_stopped is None and self.unknown_reason is None:
            raise ValueError("unknown resumption point requires an explicit reason")
        if self.where_execution_stopped is not None and not self.source_evidence:
            raise ValueError("known resumption point requires source evidence")
        if not self.verify_digest():
            raise ValueError("resumption point digest mismatch")
        return self


class ExecutionContextPackV1(DigestBoundModel):
    digest_field = "context_digest"

    contract_id: Literal["atlas.execution-context-pack"] = "atlas.execution-context-pack"
    schema_version: Literal["1.0"] = "1.0"
    target_work_item: OperationalRecordRefV1
    desired_outcome: str
    why_it_matters: str
    effective_work_state: EffectiveWorkState
    confidence: ConfidenceAssessment
    freshness: FreshnessAssessmentV1
    most_recent_material_change: str | None = None
    prior_decisions: tuple[str, ...] = ()
    completed_work: tuple[str, ...] = ()
    remaining_work: tuple[str, ...] = ()
    current_blocker_or_dependency: tuple[str, ...] = ()
    delegated_work: tuple[str, ...] = ()
    stakeholders: tuple[str, ...] = ()
    relevant_records_and_evidence: tuple[str, ...] = ()
    unresolved_questions: tuple[str, ...] = ()
    recommended_next_action: str | None = None
    resumption_point: ResumptionPointV1
    stale_context_warning: str | None = None
    redaction_warning: str | None = None
    context_digest: str = Field(pattern=r"^[0-9a-f]{64}$")

    @classmethod
    def create(cls, **values: Any) -> ExecutionContextPackV1:
        return cls(context_digest=cls.compute_digest(values), **values)

    @model_validator(mode="after")
    def validate_context(self) -> ExecutionContextPackV1:
        if not self.relevant_records_and_evidence:
            raise ValueError("context pack requires evidence references")
        if not self.verify_digest():
            raise ValueError("execution context digest mismatch")
        return self
