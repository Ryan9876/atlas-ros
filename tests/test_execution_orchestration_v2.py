from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from hypothesis import given
from hypothesis import strategies as st
from pydantic import ValidationError

from atlas_ros.adapters.notion import FakeNotionAdapter, NotionPage
from atlas_ros.adapters.notion_execution import (
    NotionExecutionAdapterV2,
    NotionMappingContract,
)
from atlas_ros.contracts import (
    ErrorClassification,
    ExecutionAuthorizationV2,
    ExecutionReceiptV2,
    ProviderName,
    ProviderOperation,
    ProviderOperationType,
    TransactionStateV2,
    deterministic_digest,
)
from atlas_ros.orchestration import (
    ExecutionOrchestratorV2,
    FakeExecutionProvider,
    FaultMode,
    InMemoryExecutionStore,
    ProviderExecutionError,
)


def operation(
    sequence: int,
    operation_type: ProviderOperationType,
    *,
    provider: ProviderName = ProviderName.TODOIST,
    compensation_allowed: bool = False,
) -> ProviderOperation:
    operation_id = f"{provider.value}:{sequence}:{operation_type.value}"
    return ProviderOperation(
        operation_id=operation_id,
        provider=provider,
        operation_type=operation_type,
        sequence=sequence,
        payload={"identity": "A-1", "properties": {"Action ID": "A-1"}}
        if provider == ProviderName.NOTION
        else {"value": sequence},
        idempotency_key=deterministic_digest({"operation_id": operation_id}),
        compensation_allowed=compensation_allowed,
    )


def execution(
    provider: FakeExecutionProvider,
    operations: tuple[ProviderOperation, ...],
    *,
    actor: str = "Ryan",
    store: InMemoryExecutionStore | None = None,
):
    plan_digest = deterministic_digest({"plan": "A-1", "revision": 1})
    authorization = ExecutionOrchestratorV2.issue_authorization(
        plan_id="plan-A-1",
        plan_digest=plan_digest,
        action_id="A-1",
        correlation_id="correlation-A-1",
        operations=operations,
        reason="Attended test execution",
        attended_confirmation_evidence="Ryan selected the exact execution action.",
        actor_identity=actor,
    )
    command = ExecutionOrchestratorV2.build_command(
        plan_id="plan-A-1",
        plan_digest=plan_digest,
        action_id="A-1",
        correlation_id="correlation-A-1",
        authorization=authorization,
        operations=operations,
    )
    orchestrator = ExecutionOrchestratorV2((provider,), store=store)
    return orchestrator, command, authorization


def resign(authorization: ExecutionAuthorizationV2, **changes: Any) -> ExecutionAuthorizationV2:
    changed = authorization.model_copy(update={**changes, "authorization_digest": "0" * 64})
    return changed.model_copy(
        update={"authorization_digest": deterministic_digest(changed.digest_payload())}
    )


def test_exact_authorization_and_verified_receipt() -> None:
    operations = (
        operation(1, ProviderOperationType.UPSERT_PARENT),
        operation(2, ProviderOperationType.VERIFY_HIERARCHY),
    )
    provider = FakeExecutionProvider(ProviderName.TODOIST)
    orchestrator, command, authorization = execution(provider, operations)
    transaction, receipt = orchestrator.execute(command, authorization)
    assert transaction.state == TransactionStateV2.VERIFIED
    assert receipt.applied and receipt.readback_verified and receipt.verify_digest()
    assert receipt.operations_requested == receipt.operations_applied
    assert all(entry.verify_digest() for entry in transaction.journal)
    assert len(provider.objects) == 2


def test_verified_replay_is_idempotent() -> None:
    operations = (operation(1, ProviderOperationType.UPSERT_PARENT),)
    provider = FakeExecutionProvider(ProviderName.TODOIST)
    store = InMemoryExecutionStore()
    orchestrator, command, authorization = execution(provider, operations, store=store)
    first = orchestrator.execute(command, authorization)
    second = orchestrator.execute(command, authorization)
    assert first == second
    assert len(provider.objects) == 1
    assert provider.attempts[operations[0].operation_id] == 1


def test_one_time_authorization_rejects_replay() -> None:
    operations = (operation(1, ProviderOperationType.UPSERT_PARENT),)
    provider = FakeExecutionProvider(ProviderName.TODOIST)
    orchestrator, command, authorization = execution(provider, operations)
    authorization = resign(authorization, replay_policy="one_time")
    command = command.model_copy(
        update={
            "authorization_digest": authorization.authorization_digest,
            "command_digest": "0" * 64,
        }
    )
    command = command.model_copy(
        update={"command_digest": deterministic_digest(command.digest_payload())}
    )
    orchestrator.execute(command, authorization)
    with pytest.raises(PermissionError, match="one-time"):
        orchestrator.execute(command, authorization)


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ({"actor_identity": "Alex"}, "actor"),
        ({"execution_plan_id": "plan-other"}, "exact execution plan"),
        ({"execution_plan_digest": "1" * 64}, "exact execution plan"),
        ({"action_id": "A-2"}, "action"),
        ({"revoked": True}, "revoked"),
        (
            {"expires_at": datetime.now(UTC) - timedelta(seconds=1)},
            "expired",
        ),
        ({"maximum_object_count": 0}, "object count"),
        ({"provider_scope": frozenset()}, "provider scope"),
        ({"operation_types": frozenset()}, "operation scope"),
    ],
)
def test_authorization_fails_closed(change: dict[str, Any], message: str) -> None:
    operations = (operation(1, ProviderOperationType.UPSERT_PARENT),)
    provider = FakeExecutionProvider(ProviderName.TODOIST)
    orchestrator, command, authorization = execution(provider, operations)
    changed = resign(authorization, **change)
    command = command.model_copy(
        update={
            "authorization_id": changed.authorization_id,
            "authorization_digest": changed.authorization_digest,
            "command_digest": "0" * 64,
        }
    )
    command = command.model_copy(
        update={"command_digest": deterministic_digest(command.digest_payload())}
    )
    with pytest.raises(PermissionError, match=message):
        orchestrator.execute(command, changed)
    assert provider.operation_log == []


def test_command_digest_change_requires_new_authorization() -> None:
    operations = (operation(1, ProviderOperationType.UPSERT_PARENT),)
    provider = FakeExecutionProvider(ProviderName.TODOIST)
    orchestrator, command, authorization = execution(provider, operations)
    changed = command.model_copy(update={"execution_plan_digest": "2" * 64})
    with pytest.raises(ValueError, match="command digest"):
        orchestrator.execute(changed, authorization)


def test_simulation_has_no_provider_writes_or_applied_receipt() -> None:
    operations = (operation(1, ProviderOperationType.UPSERT_PARENT),)
    provider = FakeExecutionProvider(ProviderName.TODOIST)
    orchestrator, command, authorization = execution(provider, operations)
    transaction, receipt = orchestrator.simulate(command, authorization)
    assert transaction.state == TransactionStateV2.SIMULATED
    assert receipt.simulation is True
    assert receipt.applied is False
    assert provider.objects == {}


@pytest.mark.parametrize(
    "fault",
    [FaultMode.RATE_LIMIT, FaultMode.SERVER_FAILURE, FaultMode.TIMEOUT_BEFORE_APPLY],
)
def test_retryable_failure_reuses_idempotency_key(fault: FaultMode) -> None:
    op = operation(1, ProviderOperationType.UPSERT_PARENT)
    provider = FakeExecutionProvider(
        ProviderName.TODOIST,
        {op.operation_id: (fault, FaultMode.SUCCESS)},
    )
    orchestrator, command, authorization = execution(provider, (op,))
    transaction, receipt = orchestrator.execute(command, authorization)
    assert transaction.state == TransactionStateV2.VERIFIED
    assert receipt.attempt_counts[op.operation_id] == 2
    assert len(provider.objects) == 1
    assert any(entry.event_type == "retry_scheduled" for entry in transaction.journal)


def test_timeout_after_apply_recovers_by_readback_without_duplicate() -> None:
    op = operation(1, ProviderOperationType.UPSERT_PARENT)
    provider = FakeExecutionProvider(
        ProviderName.TODOIST,
        {op.operation_id: (FaultMode.TIMEOUT_AFTER_APPLY,)},
    )
    orchestrator, command, authorization = execution(provider, (op,))
    transaction, receipt = orchestrator.execute(command, authorization)
    assert transaction.state == TransactionStateV2.VERIFIED
    assert receipt.applied
    assert len(provider.objects) == 1
    assert provider.attempts[op.operation_id] == 1


@pytest.mark.parametrize(
    "fault",
    [
        FaultMode.VALIDATION_FAILURE,
        FaultMode.PERMISSION_FAILURE,
        FaultMode.SCHEMA_DRIFT,
        FaultMode.READBACK_MISMATCH,
    ],
)
def test_non_retryable_failure_never_reports_success(fault: FaultMode) -> None:
    op = operation(1, ProviderOperationType.UPSERT_PARENT)
    provider = FakeExecutionProvider(
        ProviderName.TODOIST,
        {op.operation_id: (fault,)},
    )
    orchestrator, command, authorization = execution(provider, (op,))
    transaction, receipt = orchestrator.execute(command, authorization)
    assert transaction.state == TransactionStateV2.FAILED
    assert receipt.applied is False
    assert receipt.readback_verified is False


def test_partial_failure_requires_manual_recovery_without_compensation_scope() -> None:
    first = operation(1, ProviderOperationType.UPSERT_PARENT)
    second = operation(2, ProviderOperationType.UPSERT_CHILD)
    provider = FakeExecutionProvider(
        ProviderName.TODOIST,
        {second.operation_id: (FaultMode.VALIDATION_FAILURE,)},
    )
    orchestrator, command, authorization = execution(provider, (first, second))
    transaction, receipt = orchestrator.execute(command, authorization)
    assert transaction.state == TransactionStateV2.MANUAL_RECOVERY_REQUIRED
    assert transaction.recovery_instructions
    assert receipt.applied is False


def test_safe_compensation_is_recorded() -> None:
    first = operation(
        1,
        ProviderOperationType.UPSERT_PARENT,
        compensation_allowed=True,
    )
    second = operation(2, ProviderOperationType.UPSERT_CHILD)
    provider = FakeExecutionProvider(
        ProviderName.TODOIST,
        {second.operation_id: (FaultMode.VALIDATION_FAILURE,)},
    )
    orchestrator, command, authorization = execution(provider, (first, second))
    transaction, receipt = orchestrator.execute(command, authorization)
    assert transaction.state == TransactionStateV2.COMPENSATED
    assert provider.compensation_log == [first.operation_id]
    assert receipt.compensation_result == "compensated"
    assert receipt.applied is False


def test_compensation_failure_requires_manual_recovery() -> None:
    first = operation(
        1,
        ProviderOperationType.UPSERT_PARENT,
        compensation_allowed=True,
    )
    second = operation(2, ProviderOperationType.UPSERT_CHILD)
    provider = FakeExecutionProvider(
        ProviderName.TODOIST,
        {
            first.operation_id: (FaultMode.SUCCESS, FaultMode.COMPENSATION_FAILURE),
            second.operation_id: (FaultMode.VALIDATION_FAILURE,),
        },
    )
    orchestrator, command, authorization = execution(provider, (first, second))
    transaction, receipt = orchestrator.execute(command, authorization)
    assert transaction.state == TransactionStateV2.MANUAL_RECOVERY_REQUIRED
    assert transaction.recovery_instructions
    assert receipt.applied is False


def test_duplicate_active_command_is_rejected() -> None:
    operations = (operation(1, ProviderOperationType.UPSERT_PARENT),)
    provider = FakeExecutionProvider(ProviderName.TODOIST)
    store = InMemoryExecutionStore()
    orchestrator, command, authorization = execution(provider, operations, store=store)
    store.active_commands.add(command.command_id)
    with pytest.raises(RuntimeError, match="already active"):
        orchestrator.execute(command, authorization)


def test_false_success_receipt_is_rejected() -> None:
    with pytest.raises(ValidationError, match="verified transaction state"):
        ExecutionReceiptV2(
            receipt_id="receipt",
            transaction_id="transaction",
            command_id="command",
            action_id="A-1",
            correlation_id="correlation",
            execution_plan_id="plan",
            execution_plan_digest="a" * 64,
            authorization_id="authorization",
            authorization_digest="b" * 64,
            actor="Ryan",
            operations_requested=("one",),
            operations_applied=("one",),
            final_transaction_state=TransactionStateV2.FAILED,
            readback_results={"one": True},
            receipt_digest="c" * 64,
            applied=True,
            readback_verified=True,
        )


@pytest.mark.parametrize("key", ["token", "Authorization", "password", "secret", "api_key"])
def test_operation_rejects_secret_fields(key: str) -> None:
    with pytest.raises(ValidationError, match="sensitive"):
        ProviderOperation(
            operation_id="op",
            provider=ProviderName.TODOIST,
            operation_type=ProviderOperationType.UPSERT_PARENT,
            sequence=1,
            payload={key: "sensitive-value"},
            idempotency_key="x" * 64,
        )


def notion_adapter() -> tuple[FakeNotionAdapter, NotionExecutionAdapterV2]:
    provider = FakeNotionAdapter()
    provider.schemas["actions"] = {
        "properties": {"Action ID": {}, "Todoist Link": {}, "Receipt": {}}
    }
    mapping = NotionMappingContract(
        data_source_id="actions",
        identity_property="Action ID",
        required_properties=("Action ID", "Todoist Link", "Receipt"),
        writable_properties=frozenset({"Action ID", "Todoist Link", "Receipt"}),
    )
    return provider, NotionExecutionAdapterV2(provider, mapping)


def notion_operation(
    operation_type: ProviderOperationType,
    sequence: int,
) -> ProviderOperation:
    return ProviderOperation(
        operation_id=f"notion:{sequence}:{operation_type}",
        provider=ProviderName.NOTION,
        operation_type=operation_type,
        sequence=sequence,
        payload={
            "identity": "A-1",
            "properties": {
                "Action ID": "A-1",
                "Todoist Link": "https://todoist.test/task-1",
            },
        },
        idempotency_key=deterministic_digest({"notion": sequence}),
    )


def test_notion_execution_adapter_upserts_and_verifies() -> None:
    provider, adapter = notion_adapter()
    context: dict[str, Any] = {}
    find = notion_operation(ProviderOperationType.FIND_RECORD, 1)
    upsert = notion_operation(ProviderOperationType.UPSERT_RECORD, 2)
    verify = notion_operation(ProviderOperationType.VERIFY_RECORD, 3)
    assert adapter.execute_operation(find, context, attempt=1).readback_verified
    applied = adapter.execute_operation(upsert, context, attempt=1)
    assert applied.applied and applied.readback_verified
    assert adapter.execute_operation(verify, context, attempt=1).readback_verified
    assert len(provider.pages) == 1
    recovered = adapter.readback_before_retry(upsert, {})
    assert recovered is not None and recovered.applied


def test_notion_schema_drift_fails_closed() -> None:
    provider, adapter = notion_adapter()
    provider.schemas["actions"] = {"properties": {"Action ID": {}}}
    with pytest.raises(ProviderExecutionError) as failure:
        adapter.execute_operation(
            notion_operation(ProviderOperationType.FIND_RECORD, 1),
            {},
            attempt=1,
        )
    assert failure.value.classification == ErrorClassification.SCHEMA_MISMATCH


def test_notion_mapping_rejects_unowned_fields() -> None:
    _, adapter = notion_adapter()
    op = notion_operation(ProviderOperationType.UPSERT_RECORD, 1)
    op = op.model_copy(
        update={
            "payload": {
                "identity": "A-1",
                "properties": {"Checkpoint": "unauthorized"},
            }
        }
    )
    with pytest.raises(ProviderExecutionError) as failure:
        adapter.execute_operation(op, {}, attempt=1)
    assert failure.value.classification == ErrorClassification.VALIDATION_FAILURE


def test_notion_duplicate_identity_fails_closed() -> None:
    provider, adapter = notion_adapter()
    for index in range(2):
        page = NotionPage(
            id=f"page-{index}",
            url=f"https://notion.test/{index}",
            properties={"Action ID": "A-1"},
        )
        provider.pages[page.id] = page
        provider.page_sources[page.id] = "actions"
    with pytest.raises(ProviderExecutionError, match="not unique"):
        adapter.execute_operation(
            notion_operation(ProviderOperationType.FIND_RECORD, 1),
            {},
            attempt=1,
        )


@given(st.integers(min_value=1, max_value=5))
def test_replay_never_increases_provider_object_count(operation_count: int) -> None:
    operations = tuple(
        operation(index, ProviderOperationType.UPSERT_CHILD)
        for index in range(1, operation_count + 1)
    )
    provider = FakeExecutionProvider(ProviderName.TODOIST)
    orchestrator, command, authorization = execution(provider, operations)
    first = orchestrator.execute(command, authorization)
    count = len(provider.objects)
    second = orchestrator.execute(command, authorization)
    assert first == second
    assert len(provider.objects) == count == operation_count
    assert provider.operation_log == [item.operation_id for item in operations]


@given(st.text(min_size=1, max_size=20))
def test_material_plan_change_invalidates_authorization(change: str) -> None:
    operations = (operation(1, ProviderOperationType.UPSERT_PARENT),)
    provider = FakeExecutionProvider(ProviderName.TODOIST)
    orchestrator, command, authorization = execution(provider, operations)
    changed_digest = deterministic_digest({"changed_plan": change})
    changed_command = command.model_copy(
        update={"execution_plan_digest": changed_digest, "command_digest": "0" * 64}
    )
    changed_command = changed_command.model_copy(
        update={
            "command_digest": deterministic_digest(changed_command.digest_payload())
        }
    )
    with pytest.raises(PermissionError, match="exact execution plan"):
        orchestrator.execute(changed_command, authorization)


def test_serialized_evidence_contains_no_secret_values() -> None:
    operations = (operation(1, ProviderOperationType.UPSERT_PARENT),)
    provider = FakeExecutionProvider(ProviderName.TODOIST)
    orchestrator, command, authorization = execution(provider, operations)
    transaction, receipt = orchestrator.execute(command, authorization)
    serialized = transaction.model_dump_json() + receipt.model_dump_json()
    for marker in ("Bearer ", "api_key", "password", "private-token-value"):
        assert marker not in serialized
