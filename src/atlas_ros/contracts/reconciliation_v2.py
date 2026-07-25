from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .models import deterministic_digest


class AuthoritySource(StrEnum):
    TODOIST = "todoist"
    NOTION = "notion"
    DERIVED = "derived"


class UpdateDirection(StrEnum):
    TODOIST_TO_NOTION = "todoist_to_notion"
    NOTION_TO_TODOIST = "notion_to_todoist"
    DERIVE_ONLY = "derive_only"


class ConflictType(StrEnum):
    MISSING_TODOIST_OBJECT = "missing_todoist_object"
    MISSING_NOTION_RECORD = "missing_notion_record"
    AMBIGUOUS_MAPPING = "ambiguous_mapping"
    DUPLICATE_MAPPING = "duplicate_mapping"
    FIELD_AUTHORITY_VIOLATION = "field_authority_violation"
    CONCURRENT_MODIFICATION = "concurrent_modification"
    UNSUPPORTED_SCHEMA = "unsupported_schema"
    MISSING_EXECUTION_STEP = "missing_execution_step"
    AMBIGUOUS_BLOCKER = "ambiguous_blocker"
    COMMAND_REPLAY_AMBIGUITY = "command_replay_ambiguity"
    READBACK_MISMATCH = "readback_mismatch"
    PROVIDER_PERMISSION_FAILURE = "provider_permission_failure"
    STALE_CHECKPOINT = "stale_checkpoint"
    DEVELOPMENT_RECORD_DRIFT = "development_record_drift"
    RELEASE_AUTHORITY_DISAGREEMENT = "release_authority_disagreement"


class OperationStatus(StrEnum):
    APPLIED = "applied"
    ALREADY_APPLIED = "already_applied"
    FAILED = "failed"
    READBACK_MISMATCH = "readback_mismatch"


class FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class FieldAuthorityRule(FrozenModel):
    field: str = Field(min_length=1)
    authority: AuthoritySource
    direction: UpdateDirection
    normalization: Literal["identity", "text", "date", "priority", "boolean"] = "identity"
    readback_required: bool = True
    merge_allowed: bool = False


class FieldAuthorityRegistry(FrozenModel):
    policy_version: str = Field(min_length=1)
    rules: tuple[FieldAuthorityRule, ...]

    @model_validator(mode="after")
    def unique_fields(self) -> FieldAuthorityRegistry:
        fields = [rule.field for rule in self.rules]
        if len(fields) != len(set(fields)):
            raise ValueError("field-authority rules must be unique")
        return self

    @property
    def policy_digest(self) -> str:
        return deterministic_digest(
            {
                "policy_version": self.policy_version,
                "rules": [rule.model_dump(mode="json") for rule in self.rules],
            }
        )

    def rule_for(self, field: str) -> FieldAuthorityRule:
        for rule in self.rules:
            if rule.field == field:
                return rule
        raise KeyError(f"unknown reconciliation field: {field}")


class ReconciliationSnapshot(FrozenModel):
    provider: AuthoritySource
    object_id: str = Field(min_length=1)
    values: dict[str, Any]
    version: str = ""
    event_ids: tuple[str, ...] = ()
    captured_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @property
    def snapshot_digest(self) -> str:
        return deterministic_digest(
            {
                "provider": self.provider,
                "object_id": self.object_id,
                "values": self.values,
                "version": self.version,
                "event_ids": sorted(self.event_ids),
            }
        )


class ReconciliationCommand(FrozenModel):
    event_id: str = Field(min_length=1)
    kind: Literal[
        "update",
        "delegate",
        "risk",
        "blocker",
        "dependency",
        "issue",
        "unblock",
        "checkpoint",
    ]
    body: str = ""
    argument: str = ""

    @model_validator(mode="after")
    def validate_content(self) -> ReconciliationCommand:
        if (
            self.kind in {"update", "risk", "blocker", "dependency", "issue"}
            and not (self.body or self.argument).strip()
        ):
            raise ValueError(f"{self.kind} command requires content")
        if self.kind == "checkpoint":
            value = (self.argument or self.body).strip()
            try:
                datetime.fromisoformat(value)
            except ValueError as exc:
                raise ValueError("checkpoint command requires a valid ISO date") from exc
        return self

    @property
    def idempotency_key(self) -> str:
        return f"command:{self.event_id}:{deterministic_digest(self.model_dump(mode='json'))}"


class ReconciliationMutationV2(FrozenModel):
    mutation_id: str = Field(min_length=1)
    provider: AuthoritySource
    object_id: str = Field(min_length=1)
    field: str = Field(min_length=1)
    expected_value: Any = None
    desired_value: Any = None
    authority: AuthoritySource
    readback_required: bool = True
    command_event_id: str = ""
    idempotency_key: str = Field(min_length=1)


class ReconciliationConflict(FrozenModel):
    conflict_id: str = Field(min_length=1)
    plan_id: str = Field(min_length=1)
    object_id: str = Field(min_length=1)
    field_or_command: str = Field(min_length=1)
    source_value: Any = None
    target_value: Any = None
    authority_rule: str = ""
    conflict_type: ConflictType
    severity: Literal["low", "medium", "high", "critical"] = "high"
    suggested_resolution: str
    human_decision_required: bool = True
    evidence: tuple[str, ...] = ()
    status: Literal["open", "resolved", "ignored"] = "open"

    @property
    def conflict_digest(self) -> str:
        return deterministic_digest(self.model_dump(mode="json", exclude={"conflict_id"}))


class CheckpointToken(FrozenModel):
    integration: str = "todoist-notion"
    cursor: str = Field(min_length=1)
    applied_event_ids: tuple[str, ...] = ()
    integrity_digest: str = ""

    @model_validator(mode="after")
    def integrity(self) -> CheckpointToken:
        expected = deterministic_digest(
            {
                "integration": self.integration,
                "cursor": self.cursor,
                "applied_event_ids": sorted(self.applied_event_ids),
            }
        )
        if self.integrity_digest and self.integrity_digest != expected:
            raise ValueError("checkpoint integrity digest mismatch")
        object.__setattr__(self, "integrity_digest", expected)
        return self


class ReconciliationPlanV2(FrozenModel):
    plan_id: str = Field(min_length=1)
    correlation_id: str = Field(min_length=1)
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    authority_policy_version: str
    authority_policy_digest: str
    source_snapshots: tuple[ReconciliationSnapshot, ...]
    target_snapshots: tuple[ReconciliationSnapshot, ...]
    ordered_mutations: tuple[ReconciliationMutationV2, ...] = ()
    ignored_items: tuple[str, ...] = ()
    conflicts: tuple[ReconciliationConflict, ...] = ()
    command_decisions: tuple[str, ...] = ()
    required_human_decisions: tuple[str, ...] = ()
    expected_checkpoint: CheckpointToken
    plan_digest: str = ""

    @model_validator(mode="after")
    def bind_digest(self) -> ReconciliationPlanV2:
        payload = self.model_dump(mode="json", exclude={"generated_at", "plan_digest"})
        payload["conflicts"] = [
            conflict.model_dump(mode="json", exclude={"plan_id"}) for conflict in self.conflicts
        ]
        expected = deterministic_digest(payload)
        if self.plan_digest and self.plan_digest != expected:
            raise ValueError("reconciliation plan digest mismatch")
        object.__setattr__(self, "plan_digest", expected)
        return self

    @property
    def blocking(self) -> bool:
        return any(
            conflict.status == "open" and conflict.severity in {"high", "critical"}
            for conflict in self.conflicts
        )


class ReconciliationAuthorization(FrozenModel):
    authorization_id: str = Field(min_length=1)
    plan_id: str = Field(min_length=1)
    plan_digest: str = Field(min_length=64, max_length=64)
    actor: str = Field(min_length=1)
    attended: bool
    authorized_mutation_ids: tuple[str, ...]
    authorization_digest: str = ""

    @model_validator(mode="after")
    def bind_digest(self) -> ReconciliationAuthorization:
        expected = deterministic_digest(
            self.model_dump(mode="json", exclude={"authorization_digest"})
        )
        if self.authorization_digest and self.authorization_digest != expected:
            raise ValueError("authorization digest mismatch")
        object.__setattr__(self, "authorization_digest", expected)
        return self


class ReconciliationOperationResult(FrozenModel):
    mutation_id: str
    provider: AuthoritySource
    object_id: str
    status: OperationStatus
    expected_value: Any = None
    actual_value: Any = None
    verified: bool = False
    error: str = ""


class ReconciliationReceiptV2(FrozenModel):
    receipt_id: str = Field(min_length=1)
    plan_id: str
    plan_digest: str
    authorization_id: str
    authorization_digest: str
    correlation_id: str
    authority_policy_version: str
    source_checkpoint: CheckpointToken
    resulting_checkpoint: CheckpointToken
    planned_count: int = Field(ge=0)
    applied_count: int = Field(ge=0)
    verified_count: int = Field(ge=0)
    conflict_count: int = Field(ge=0)
    ignored_count: int = Field(ge=0)
    operation_results: tuple[ReconciliationOperationResult, ...]
    checkpoint_advanced: bool
    recovery_instructions: tuple[str, ...] = ()
    consistent: bool
    receipt_digest: str = ""

    @model_validator(mode="after")
    def verify_consistency_and_digest(self) -> ReconciliationReceiptV2:
        can_be_consistent = (
            self.conflict_count == 0
            and self.verified_count == self.planned_count
            and self.checkpoint_advanced
            and all(result.verified for result in self.operation_results)
        )
        if self.consistent and not can_be_consistent:
            raise ValueError("consistent receipt requires complete verified readback")
        expected = deterministic_digest(self.model_dump(mode="json", exclude={"receipt_digest"}))
        if self.receipt_digest and self.receipt_digest != expected:
            raise ValueError("reconciliation receipt digest mismatch")
        object.__setattr__(self, "receipt_digest", expected)
        return self


class ReconciliationResultV2(FrozenModel):
    plan: ReconciliationPlanV2
    receipt: ReconciliationReceiptV2

    @property
    def consistent(self) -> bool:
        return self.receipt.consistent
