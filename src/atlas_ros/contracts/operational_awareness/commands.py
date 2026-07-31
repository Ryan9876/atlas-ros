"""Explicit Atlas lifecycle command contracts."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import Field, model_validator

from atlas_ros.contracts.advisory_v1 import ConfidenceAssessment, ProvenanceRecord

from .base import AtlasCommandType, AuthoritativeSystem, DigestBoundModel
from .records import OperationalRecordRefV1


class CommandSourceRefV1(DigestBoundModel):
    digest_field = "source_digest"
    digest_excluded_fields = frozenset({"source_retrieved_at"})

    contract_id: Literal["atlas.command-source-ref"] = "atlas.command-source-ref"
    schema_version: Literal["1.0"] = "1.0"
    source_provider: AuthoritativeSystem
    source_task_id: str
    source_task_revision: str
    source_command_text: str
    parent_task_id: str | None = None
    source_event_id: str | None = None
    source_event_type: str | None = None
    source_comment_id: str | None = None
    source_author_identity: str | None = None
    source_posted_at: str | None = None
    source_retrieved_at: str | None = None
    source_timezone: str | None = None
    parent_action_record_id: str | None = None
    parent_action_record_url: str | None = None
    parent_outcome_title: str | None = None
    source_digest: str = Field(pattern=r"^[0-9a-f]{64}$")

    @classmethod
    def create(cls, **values: Any) -> CommandSourceRefV1:
        return cls(source_digest=cls.compute_digest(values), **values)

    @model_validator(mode="after")
    def validate_digest(self) -> CommandSourceRefV1:
        if not self.verify_digest():
            raise ValueError("command source digest mismatch")
        return self


class AtlasCommandV1(DigestBoundModel):
    digest_field = "command_digest"
    digest_excluded_fields = frozenset({"idempotency_identity"})

    contract_id: Literal["atlas.command"] = "atlas.command"
    schema_version: Literal["1.0"] = "1.0"
    command_type: AtlasCommandType
    source: CommandSourceRefV1
    subject: str | None = None
    fields: dict[str, str] = Field(default_factory=dict)
    command_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    idempotency_identity: str

    @classmethod
    def create(cls, **values: Any) -> AtlasCommandV1:
        digest = cls.compute_digest(values)
        return cls(command_digest=digest, idempotency_identity=f"atlas-command:{digest}", **values)

    @model_validator(mode="after")
    def validate_command(self) -> AtlasCommandV1:
        if self.idempotency_identity != f"atlas-command:{self.command_digest}":
            raise ValueError("command idempotency identity mismatch")
        if not self.verify_digest():
            raise ValueError("command digest mismatch")
        return self


class CommandInterpretationV1(DigestBoundModel):
    digest_field = "interpretation_digest"

    contract_id: Literal["atlas.command-interpretation"] = "atlas.command-interpretation"
    schema_version: Literal["1.0"] = "1.0"
    command: AtlasCommandV1
    parent_outcome: OperationalRecordRefV1 | None = None
    affected_notion_record: OperationalRecordRefV1 | None = None
    responsible_party: str | None = None
    accountable_party: str | None = None
    expected_outcome: str | None = None
    completion_criteria: tuple[str, ...] = ()
    delegate_due: str | None = None
    follow_up_checkpoint: str | None = None
    next_checkpoint: str | None = None
    next_ryan_owned_action: str | None = None
    provenance: tuple[ProvenanceRecord, ...] = ()
    confidence: ConfidenceAssessment
    ambiguity: tuple[str, ...] = ()
    blockers: tuple[str, ...] = ()
    interpretation_digest: str = Field(pattern=r"^[0-9a-f]{64}$")

    @classmethod
    def create(cls, **values: Any) -> CommandInterpretationV1:
        return cls(interpretation_digest=cls.compute_digest(values), **values)

    @model_validator(mode="after")
    def validate_interpretation(self) -> CommandInterpretationV1:
        if self.ambiguity and not self.blockers:
            raise ValueError("ambiguous interpretation must fail closed with blockers")
        if (
            self.follow_up_checkpoint is not None
            and self.next_checkpoint is not None
            and self.follow_up_checkpoint != self.next_checkpoint
        ):
            raise ValueError("next_checkpoint must remain the follow-up compatibility alias")
        if not self.verify_digest():
            raise ValueError("command interpretation digest mismatch")
        return self


class TaskUpdateLifecycleNormalizationV1(DigestBoundModel):
    """Deterministic, provider-free normalization of one task update.

    The result is a proposal only. It cannot authorize planning or execution.
    """

    digest_field = "normalization_digest"

    contract_id: Literal["atlas.task-update-lifecycle-normalization"] = (
        "atlas.task-update-lifecycle-normalization"
    )
    schema_version: Literal["1.0"] = "1.0"
    source: CommandSourceRefV1
    classification: AtlasCommandType
    proposed_command: AtlasCommandV1
    actionable_transition: bool
    responsible_party: str | None = None
    accountable_party: str | None = None
    expected_outcome: str | None = None
    completion_criteria: tuple[str, ...] = ()
    delegate_due: str | None = None
    follow_up_checkpoint: str | None = None
    confidence: ConfidenceAssessment
    provenance: tuple[ProvenanceRecord, ...] = ()
    evidence: tuple[str, ...] = ()
    ambiguity: tuple[str, ...] = ()
    blockers: tuple[str, ...] = ()
    field_origins: dict[str, str] = Field(default_factory=dict)
    requires_attended_approval: bool = False
    resolved_follow_up_date: str | None = None
    normalization_digest: str = Field(pattern=r"^[0-9a-f]{64}$")

    @classmethod
    def create(cls, **values: Any) -> TaskUpdateLifecycleNormalizationV1:
        return cls(normalization_digest=cls.compute_digest(values), **values)

    @model_validator(mode="after")
    def validate_normalization(self) -> TaskUpdateLifecycleNormalizationV1:
        if self.proposed_command.command_type != self.classification:
            raise ValueError("normalization classification must match proposed command")
        if self.ambiguity and not self.blockers:
            raise ValueError("ambiguous normalization must fail closed with blockers")
        if self.classification == AtlasCommandType.DELEGATE and not self.blockers:
            if not self.responsible_party:
                raise ValueError("qualified delegation requires a responsible party")
            if not self.expected_outcome:
                raise ValueError("qualified delegation requires an expected outcome")
            if not self.completion_criteria:
                raise ValueError("qualified delegation requires completion criteria")
        if not self.verify_digest():
            raise ValueError("task-update normalization digest mismatch")
        return self
