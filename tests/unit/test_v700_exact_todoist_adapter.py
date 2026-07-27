from __future__ import annotations

import pytest

from atlas_ros.adapters.exact_todoist import (
    ExactTodoistExecutionAdapter,
    ExactTodoistExecutionError,
    todoist_target,
)
from atlas_ros.adapters.payloads import (
    ExecutionPayloadError,
    InMemoryExecutionPayloadStore,
)
from atlas_ros.adapters.todoist import FakeTodoistAdapter
from atlas_ros.application.execution import AttendedExecutionService
from atlas_ros.contracts.execution.payload import ProviderOperationPayload
from atlas_ros.contracts.execution.transaction import (
    AuthorizedExecutionPlan,
    PlannedProviderOperation,
)


def payload(
    operation_id: str = "operation-1",
    **overrides: object,
) -> ProviderOperationPayload:
    values: dict[str, object] = {
        "content": "Implement the exact adapter",
        "project_id": "work",
        "section_id": None,
        "parent_id": None,
        "description": "Checksum-bound attended work",
    }
    values.update(overrides)
    return ProviderOperationPayload.create(
        operation_id=operation_id,
        payload=values,
    )


def operation(value: ProviderOperationPayload) -> PlannedProviderOperation:
    data = value.data
    return PlannedProviderOperation(
        operation_id=value.operation_id,
        sequence=0,
        provider="todoist",
        action="create",
        target=todoist_target(
            str(data["project_id"]),
            section_id=data.get("section_id"),
            parent_id=data.get("parent_id"),
        ),
        payload_digest=value.payload_digest,
        idempotency_key=f"capture-1:{value.operation_id}",
    )


def test_exact_adapter_executes_only_registered_payload_content() -> None:
    exact_payload = payload()
    store = InMemoryExecutionPayloadStore()
    store.register(exact_payload)
    client = FakeTodoistAdapter()
    planned = operation(exact_payload)
    authorized = AuthorizedExecutionPlan.create(
        authorization_id="authorization-1",
        operations=(planned,),
    )

    receipt = AttendedExecutionService(
        ExactTodoistExecutionAdapter(client, store)
    ).execute(authorized, transaction_id="transaction-1")

    task = client.get_task(receipt.operation_receipts[0].provider_record_id)
    assert task.content == "Implement the exact adapter"
    assert task.project_id == "work"
    assert task.description == "Checksum-bound attended work"
    assert receipt.provider_writes == 1
    assert receipt.operation_receipts[0].write_digest == (
        receipt.operation_receipts[0].readback_digest
    )


def test_payload_store_rejects_digest_substitution() -> None:
    exact_payload = payload()
    store = InMemoryExecutionPayloadStore()
    store.register(exact_payload)
    substituted = operation(exact_payload).model_copy(
        update={"payload_digest": "f" * 64}
    )

    with pytest.raises(ExecutionPayloadError, match="digest disagrees"):
        store.resolve(substituted)


def test_exact_adapter_rejects_payload_fields_it_did_not_define() -> None:
    exact_payload = payload(priority=4)
    store = InMemoryExecutionPayloadStore()
    store.register(exact_payload)

    with pytest.raises(ExactTodoistExecutionError, match="unsupported fields"):
        ExactTodoistExecutionAdapter(FakeTodoistAdapter(), store).write(
            operation(exact_payload),
            authorization_id="authorization-1",
            transaction_id="transaction-1",
        )


def test_exact_adapter_rejects_target_substitution() -> None:
    exact_payload = payload()
    store = InMemoryExecutionPayloadStore()
    store.register(exact_payload)
    substituted = operation(exact_payload).model_copy(
        update={"target": "project:personal"}
    )

    with pytest.raises(ExactTodoistExecutionError, match="target disagrees"):
        ExactTodoistExecutionAdapter(FakeTodoistAdapter(), store).write(
            substituted,
            authorization_id="authorization-1",
            transaction_id="transaction-1",
        )


def test_payload_contract_rejects_noncanonical_or_tampered_content() -> None:
    exact_payload = payload()
    raw = exact_payload.model_dump(mode="json")
    raw["payload_json"] = '{"project_id":"work", "content":"changed"}'

    with pytest.raises(ValueError, match="canonical|digest"):
        ProviderOperationPayload.model_validate(raw)
