from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .models import deterministic_digest


def _now() -> datetime:
    return datetime.now(UTC)


def stable_id(prefix: str, payload: Any) -> str:
    return f"{prefix}-{deterministic_digest(payload)[:32]}"


class ProviderName(StrEnum):
    TODOIST = "todoist"
    NOTION = "notion"


class ProviderOperationType(StrEnum):
    RESOLVE_TARGET = "resolve_target"
    READ_PARENT = "read_parent"
    UPSERT_PARENT = "upsert_parent"
    VERIFY_PARENT = "verify_parent"
    READ_CHILDREN = "read_children"
    UPSERT_CHILD = "upsert_child"
    VERIFY_CHILD = "verify_child"
    VERIFY_HIERARCHY = "verify_hierarchy"
    MOVE_GROUP = "move_group"
    FIND_RECORD = "find_record"
    UPSERT_RECORD = "upsert_record"
    WRITE_LINK = "write_link"
    VERIFY_RECORD = "verify_record"


class ErrorClassification(StrEnum):
    RETRYABLE_TRANSPORT = "retryable_transport"
    RETRYABLE_TIMEOUT = "retryable_timeout"
    RETRYABLE_RATE_LIMIT = "retryable_rate_limit"
    RETRYABLE_PROVIDER_5XX = "retryable_provider_5xx"
    VALIDATION_FAILURE = "validation_failure"
    AUTHORIZATION_FAILURE = "authorization_failure"
    SCHEMA_MISMATCH = "schema_mismatch"
    PERMISSION_FAILURE = "permission_failure"
    READBACK_MISMATCH = "readback_mismatch"
    UNKNOWN_REVIEW = "unknown_review"

    @property
    def retryable(self) -> bool:
        return self in {
            ErrorClassification.RETRYABLE_TRANSPORT,
            ErrorClassification.RETRYABLE_TIMEOUT,
            ErrorClassification.RETRYABLE_RATE_LIMIT,
            ErrorClassification.RETRYABLE_PROVIDER_5XX,
        }


class TransactionStateV2(StrEnum):
    PREPARED = "prepared"
    AUTHORIZATION_VALIDATED = "authorization_validated"
    APPLYING = "applying"
    VERIFYING = "verifying"
    VERIFIED = "verified"
    RETRY_PENDING = "retry_pending"
    PARTIALLY_APPLIED = "partially_applied"
    COMPENSATING = "compensating"
    COMPENSATED = "compensated"
    FAILED = "failed"
    MANUAL_RECOVERY_REQUIRED = "manual_recovery_required"
    SIMULATED = "simulated"


LEGAL_TRANSITIONS: dict[TransactionStateV2, frozenset[TransactionStateV2]] = {
    TransactionStateV2.PREPARED: frozenset(
        {TransactionStateV2.AUTHORIZATION_VALIDATED, TransactionStateV2.FAILED}
    ),
    TransactionStateV2.AUTHORIZATION_VALIDATED: frozenset(
        {TransactionStateV2.APPLYING, TransactionStateV2.FAILED}
    ),
    TransactionStateV2.APPLYING: frozenset(
        {
            TransactionStateV2.APPLYING,
            TransactionStateV2.VERIFYING,
            TransactionStateV2.RETRY_PENDING,
            TransactionStateV2.PARTIALLY_APPLIED,
            TransactionStateV2.FAILED,
            TransactionStateV2.SIMULATED,
        }
    ),
    TransactionStateV2.VERIFYING: frozenset(
        {
            TransactionStateV2.VERIFYING,
            TransactionStateV2.VERIFIED,
            TransactionStateV2.APPLYING,
            TransactionStateV2.RETRY_PENDING,
            TransactionStateV2.PARTIALLY_APPLIED,
            TransactionStateV2.FAILED,
            TransactionStateV2.SIMULATED,
        }
    ),
    TransactionStateV2.RETRY_PENDING: frozenset(
        {
            TransactionStateV2.APPLYING,
            TransactionStateV2.VERIFYING,
            TransactionStateV2.PARTIALLY_APPLIED,
            TransactionStateV2.FAILED,
        }
    ),
    TransactionStateV2.PARTIALLY_APPLIED: frozenset(
        {
            TransactionStateV2.COMPENSATING,
            TransactionStateV2.MANUAL_RECOVERY_REQUIRED,
            TransactionStateV2.FAILED,
        }
    ),
    TransactionStateV2.COMPENSATING: frozenset(
        {
            TransactionStateV2.COMPENSATED,
            TransactionStateV2.MANUAL_RECOVERY_REQUIRED,
            TransactionStateV2.FAILED,
        }
    ),
    TransactionStateV2.COMPENSATED: frozenset(),
    TransactionStateV2.VERIFIED: frozenset(),
    TransactionStateV2.FAILED: frozenset(),
    TransactionStateV2.MANUAL_RECOVERY_REQUIRED: frozenset(),
    TransactionStateV2.SIMULATED: frozenset(),
}


class ProviderOperation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    operation_id: str = Field(min_length=1, max_length=256)
    provider: ProviderName
    operation_type: ProviderOperationType
    sequence: int = Field(ge=1)
    payload: dict[str, Any] = Field(default_factory=dict)
    idempotency_key: str = Field(min_length=16, max_length=256)
    requires_readback: bool = True
    destructive: bool = False
    compensation_allowed: bool = False

    @model_validator(mode="after")
    def reject_sensitive_payload(self) -> ProviderOperation:
        forbidden = {"token", "authorization", "password", "secret", "api_key", "cookie"}
        keys = {str(key).casefold() for key in self.payload}
        if keys & forbidden:
            raise ValueError("provider operation payload contains prohibited sensitive fields")
        return self


class ExecutionAuthorizationV2(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    contract_version: Literal[2] = 2
    authorization_id: str = Field(min_length=1, max_length=256)
    actor_identity: str = Field(min_length=1, max_length=200)
    actor_authority: str = Field(min_length=1, max_length=200)
    execution_plan_id: str = Field(min_length=1, max_length=256)
    execution_plan_digest: str = Field(min_length=64, max_length=64)
    action_id: str = Field(min_length=1, max_length=256)
    provider_scope: frozenset[ProviderName]
    operation_types: frozenset[ProviderOperationType]
    maximum_object_count: int = Field(ge=0, le=100)
    reason: str = Field(min_length=1, max_length=2_000)
    attended_confirmation_evidence: str = Field(min_length=1, max_length=2_000)
    issued_at: datetime = Field(default_factory=_now)
    expires_at: datetime | None = None
    replay_policy: Literal["one_time", "idempotent_replay"] = "one_time"
    correlation_id: str = Field(min_length=1, max_length=256)
    revoked: bool = False
    authorization_digest: str = Field(min_length=64, max_length=64)

    def digest_payload(self) -> dict[str, Any]:
        return self.model_dump(mode="json", exclude={"authorization_digest"})

    def verify_digest(self) -> bool:
        return self.authorization_digest == deterministic_digest(self.digest_payload())

    def validate_for(
        self,
        *,
        plan_id: str,
        plan_digest: str,
        action_id: str,
        operations: tuple[ProviderOperation, ...],
        at: datetime | None = None,
    ) -> None:
        now = at or _now()
        if not self.verify_digest():
            raise PermissionError("authorization digest verification failed")
        if self.actor_identity.casefold() != "ryan":
            raise PermissionError("canonical execution actor must be Ryan")
        if self.actor_authority != "production_promotion_owner":
            raise PermissionError("actor lacks canonical attended execution authority")
        if self.revoked:
            raise PermissionError("authorization was revoked")
        if self.expires_at is not None and now > self.expires_at:
            raise PermissionError("authorization expired")
        if self.execution_plan_id != plan_id or self.execution_plan_digest != plan_digest:
            raise PermissionError("authorization is not bound to the exact execution plan")
        if self.action_id != action_id:
            raise PermissionError("authorization action differs from command")
        if len(operations) > self.maximum_object_count:
            raise PermissionError("command exceeds authorized object count")
        providers = {operation.provider for operation in operations}
        operation_types = {operation.operation_type for operation in operations}
        if not providers <= self.provider_scope:
            raise PermissionError("command exceeds authorized provider scope")
        if not operation_types <= self.operation_types:
            raise PermissionError("command exceeds authorized operation scope")
        if any(
            operation.destructive and not operation.compensation_allowed for operation in operations
        ):
            raise PermissionError("destructive operation lacks explicit compensation authorization")


class ExecutionCommandV2(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    contract_version: Literal[2] = 2
    command_id: str = Field(min_length=1, max_length=256)
    execution_plan_id: str = Field(min_length=1, max_length=256)
    execution_plan_digest: str = Field(min_length=64, max_length=64)
    authorization_id: str = Field(min_length=1, max_length=256)
    authorization_digest: str = Field(min_length=64, max_length=64)
    action_id: str = Field(min_length=1, max_length=256)
    correlation_id: str = Field(min_length=1, max_length=256)
    operations: tuple[ProviderOperation, ...]
    expected_final_state: Literal["verified"] = "verified"
    idempotency_key: str = Field(min_length=16, max_length=256)
    created_at: datetime = Field(default_factory=_now)
    command_digest: str = Field(min_length=64, max_length=64)

    @model_validator(mode="after")
    def validate_command(self) -> ExecutionCommandV2:
        sequence = [operation.sequence for operation in self.operations]
        if sequence != list(range(1, len(sequence) + 1)):
            raise ValueError("provider operations must use contiguous one-based sequence")
        if len({operation.operation_id for operation in self.operations}) != len(self.operations):
            raise ValueError("provider operation identities must be unique")
        return self

    def digest_payload(self) -> dict[str, Any]:
        return self.model_dump(mode="json", exclude={"created_at", "command_digest"})

    def verify_digest(self) -> bool:
        return self.command_digest == deterministic_digest(self.digest_payload())


class ProviderOperationResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    operation_id: str
    provider: ProviderName
    operation_type: ProviderOperationType
    attempt: int = Field(ge=1)
    applied: bool = False
    readback_verified: bool = False
    provider_object_references: tuple[str, ...] = ()
    evidence: dict[str, str] = Field(default_factory=dict)
    error_classification: ErrorClassification | None = None
    error_message: str = Field(default="", max_length=1_000)
    retry_eligible: bool = False

    @model_validator(mode="after")
    def validate_result(self) -> ProviderOperationResult:
        if self.applied and not self.readback_verified:
            raise ValueError("applied provider result requires verified readback")
        if self.retry_eligible and (
            self.error_classification is None or not self.error_classification.retryable
        ):
            raise ValueError("retry eligibility requires a retryable error classification")
        return self


class RecoveryInstruction(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    operation_id: str
    provider: ProviderName
    instruction: str = Field(min_length=1, max_length=2_000)
    safe_to_retry: bool = False
    required_actor: str = "Ryan"
    evidence_reference: str = Field(min_length=1, max_length=500)


class TransactionJournalEntry(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    transaction_id: str
    command_id: str
    correlation_id: str
    sequence: int = Field(ge=1)
    prior_state: TransactionStateV2
    new_state: TransactionStateV2
    operation_id: str = ""
    provider: ProviderName | None = None
    attempt: int = Field(ge=0)
    event_type: str = Field(min_length=1, max_length=100)
    result: str = Field(min_length=1, max_length=500)
    error_classification: ErrorClassification | None = None
    retry_eligible: bool = False
    provider_object_references: tuple[str, ...] = ()
    readback_status: Literal["not_required", "pending", "passed", "failed"] = "not_required"
    timestamp: datetime = Field(default_factory=_now)
    previous_entry_digest: str = ""
    entry_digest: str = Field(min_length=64, max_length=64)

    def digest_payload(self) -> dict[str, Any]:
        return self.model_dump(mode="json", exclude={"timestamp", "entry_digest"})

    def verify_digest(self) -> bool:
        return self.entry_digest == deterministic_digest(self.digest_payload())


class ExecutionTransactionV2(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    contract_version: Literal[2] = 2
    transaction_id: str
    command_id: str
    correlation_id: str
    state: TransactionStateV2
    applied_operation_ids: tuple[str, ...] = ()
    unapplied_operation_ids: tuple[str, ...] = ()
    journal: tuple[TransactionJournalEntry, ...] = ()
    recovery_instructions: tuple[RecoveryInstruction, ...] = ()

    @model_validator(mode="after")
    def validate_transaction(self) -> ExecutionTransactionV2:
        previous = ""
        for index, entry in enumerate(self.journal, 1):
            if entry.sequence != index or entry.previous_entry_digest != previous:
                raise ValueError("transaction journal chain or order is invalid")
            if not entry.verify_digest():
                raise ValueError("transaction journal entry digest is invalid")
            previous = entry.entry_digest
        if (
            self.state == TransactionStateV2.MANUAL_RECOVERY_REQUIRED
            and not self.recovery_instructions
        ):
            raise ValueError("manual recovery requires explicit recovery instructions")
        return self


class ExecutionReceiptV2(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    contract_version: Literal[2] = 2
    receipt_id: str
    transaction_id: str
    command_id: str
    action_id: str
    correlation_id: str
    execution_plan_id: str
    execution_plan_digest: str = Field(min_length=64, max_length=64)
    authorization_id: str
    authorization_digest: str = Field(min_length=64, max_length=64)
    actor: str
    operations_requested: tuple[str, ...]
    operations_applied: tuple[str, ...]
    provider_object_references: tuple[str, ...] = ()
    idempotency_digests: tuple[str, ...] = ()
    attempt_counts: dict[str, int] = Field(default_factory=dict)
    final_transaction_state: TransactionStateV2
    readback_results: dict[str, bool] = Field(default_factory=dict)
    hierarchy_verified: bool = False
    objective_done_when_verified: bool = False
    section_routing_verified: bool = False
    notion_link_verified: bool | None = None
    compensation_result: str = ""
    recovery_instructions: tuple[RecoveryInstruction, ...] = ()
    evidence_digests: tuple[str, ...] = ()
    receipt_digest: str = Field(min_length=64, max_length=64)
    applied: bool
    readback_verified: bool
    simulation: bool = False

    @model_validator(mode="after")
    def reject_false_success(self) -> ExecutionReceiptV2:
        all_readback = all(self.readback_results.values()) if self.readback_results else False
        if self.applied:
            if self.simulation:
                raise ValueError("simulation cannot produce an applied receipt")
            if self.final_transaction_state != TransactionStateV2.VERIFIED:
                raise ValueError("applied receipt requires verified transaction state")
            if set(self.operations_requested) != set(self.operations_applied):
                raise ValueError("applied receipt requires every requested operation")
            if not self.readback_verified or not all_readback:
                raise ValueError("applied receipt requires every required readback")
        return self

    def digest_payload(self) -> dict[str, Any]:
        return self.model_dump(mode="json", exclude={"receipt_digest"})

    def verify_digest(self) -> bool:
        return self.receipt_digest == deterministic_digest(self.digest_payload())
