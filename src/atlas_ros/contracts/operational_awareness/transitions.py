"""Typed lifecycle transition and provider-neutral planning contracts."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import Field, model_validator

from .base import AtlasCommandType, DigestBoundModel, EffectiveWorkState
from .commands import CommandInterpretationV1
from .records import OperationalRecordRefV1


class ProviderOperationSpecV1(DigestBoundModel):
    digest_field = "operation_digest"

    contract_id: Literal["atlas.provider-operation-spec"] = "atlas.provider-operation-spec"
    schema_version: Literal["1.0"] = "1.0"
    provider: str
    action: str
    target: str
    payload: dict[str, Any]
    idempotency_key: str
    expected_readback: dict[str, Any]
    operation_digest: str = Field(pattern=r"^[0-9a-f]{64}$")

    @classmethod
    def create(cls, **values: Any) -> ProviderOperationSpecV1:
        return cls(operation_digest=cls.compute_digest(values), **values)

    @model_validator(mode="after")
    def validate_operation(self) -> ProviderOperationSpecV1:
        if not self.expected_readback:
            raise ValueError("provider operation requires expected readback")
        if not self.verify_digest():
            raise ValueError("provider operation digest mismatch")
        return self


class DelegationTransitionV1(DigestBoundModel):
    digest_field = "transition_digest"

    contract_id: Literal["atlas.delegation-transition"] = "atlas.delegation-transition"
    schema_version: Literal["1.0"] = "1.0"
    interpretation: CommandInterpretationV1
    parent_outcome: OperationalRecordRefV1
    responsible_party: str
    accountable_party: str
    expected_outcome: str
    completion_criteria: tuple[str, ...]
    checkpoint: str | None
    resulting_state: EffectiveWorkState = EffectiveWorkState.DELEGATED
    transition_digest: str = Field(pattern=r"^[0-9a-f]{64}$")

    @classmethod
    def create(cls, **values: Any) -> DelegationTransitionV1:
        return cls(transition_digest=cls.compute_digest(values), **values)

    @model_validator(mode="after")
    def validate_transition(self) -> DelegationTransitionV1:
        if not self.completion_criteria:
            raise ValueError("delegation transition requires completion criteria")
        if not self.verify_digest():
            raise ValueError("delegation transition digest mismatch")
        return self


class WorkStateTransitionV1(DigestBoundModel):
    digest_field = "transition_digest"

    contract_id: Literal["atlas.work-state-transition"] = "atlas.work-state-transition"
    schema_version: Literal["1.0"] = "1.0"
    interpretation: CommandInterpretationV1
    target_record: OperationalRecordRefV1
    command_type: AtlasCommandType
    previous_state: EffectiveWorkState
    resulting_state: EffectiveWorkState
    reason: str
    evidence: tuple[str, ...]
    transition_digest: str = Field(pattern=r"^[0-9a-f]{64}$")

    @classmethod
    def create(cls, **values: Any) -> WorkStateTransitionV1:
        return cls(transition_digest=cls.compute_digest(values), **values)

    @model_validator(mode="after")
    def validate_transition(self) -> WorkStateTransitionV1:
        if not self.evidence:
            raise ValueError("work-state transition requires evidence")
        if not self.verify_digest():
            raise ValueError("work-state transition digest mismatch")
        return self


class NextActionProjectionV1(DigestBoundModel):
    digest_field = "projection_digest"

    contract_id: Literal["atlas.next-action-projection"] = "atlas.next-action-projection"
    schema_version: Literal["1.0"] = "1.0"
    parent_outcome: OperationalRecordRefV1
    action_title: str | None
    due_date_or_checkpoint: str | None
    reason: str
    replaces_task_ids: tuple[str, ...] = ()
    preserves_parent: bool = True
    active_checkpoint_count_after: int = Field(ge=0, le=8)
    projection_digest: str = Field(pattern=r"^[0-9a-f]{64}$")

    @classmethod
    def create(cls, **values: Any) -> NextActionProjectionV1:
        return cls(projection_digest=cls.compute_digest(values), **values)

    @model_validator(mode="after")
    def validate_projection(self) -> NextActionProjectionV1:
        if not self.preserves_parent:
            raise ValueError("lifecycle projection must preserve the parent outcome")
        if self.active_checkpoint_count_after > 1:
            raise ValueError("delegated outcomes may have only one active Ryan checkpoint")
        if not self.verify_digest():
            raise ValueError("next-action projection digest mismatch")
        return self


class TodoistLifecyclePlanV1(DigestBoundModel):
    digest_field = "plan_digest"

    contract_id: Literal["atlas.todoist-lifecycle-plan"] = "atlas.todoist-lifecycle-plan"
    schema_version: Literal["1.0"] = "1.0"
    command_interpretation: CommandInterpretationV1
    parent_outcome: OperationalRecordRefV1
    notion_operations: tuple[ProviderOperationSpecV1, ...]
    todoist_operations: tuple[ProviderOperationSpecV1, ...]
    next_action_projection: NextActionProjectionV1
    maximum_object_count: int = Field(ge=1, le=25)
    authorization_scope: str
    expected_readback: tuple[str, ...]
    compensation_behavior: str
    blockers: tuple[str, ...] = ()
    plan_digest: str = Field(pattern=r"^[0-9a-f]{64}$")

    @classmethod
    def create(cls, **values: Any) -> TodoistLifecyclePlanV1:
        return cls(plan_digest=cls.compute_digest(values), **values)

    @model_validator(mode="after")
    def validate_plan(self) -> TodoistLifecyclePlanV1:
        operation_count = len(self.notion_operations) + len(self.todoist_operations)
        if operation_count > self.maximum_object_count:
            raise ValueError("lifecycle plan exceeds its exact object budget")
        keys = tuple(
            operation.idempotency_key
            for operation in self.notion_operations + self.todoist_operations
        )
        if len(set(keys)) != len(keys):
            raise ValueError("lifecycle plan contains duplicate idempotency keys")
        if not self.expected_readback:
            raise ValueError("lifecycle plan requires readback expectations")
        if not self.verify_digest():
            raise ValueError("lifecycle plan digest mismatch")
        return self
