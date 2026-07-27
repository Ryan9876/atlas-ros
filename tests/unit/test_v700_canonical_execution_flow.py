from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from atlas_ros.application.execution import (
    AttendedAuthorizationService,
    AttendedExecutionService,
    ExecutionBoundaryError,
)
from atlas_ros.capabilities.execution_planning import ExecutionPlanningService
from atlas_ros.capabilities.input_processing import DeterministicInputProcessor
from atlas_ros.capabilities.reconciliation import CanonicalReconciliationService
from atlas_ros.contracts.digests import sha256_digest
from atlas_ros.contracts.execution.pipeline import CaptureEnvelope
from atlas_ros.contracts.execution.transaction import (
    PlannedProviderOperation,
    ProviderReadbackReceipt,
    ProviderWriteReceipt,
)


@dataclass(frozen=True)
class AllowWriteGuard:
    def require_provider_write_permission(self, authorization_id: str | None) -> None:
        if not authorization_id:
            raise PermissionError("authorization is required")


@dataclass
class FakeProviderPort:
    calls: list[str] = field(default_factory=list)

    def write(
        self,
        operation: PlannedProviderOperation,
        *,
        authorization_id: str,
        transaction_id: str,
    ) -> ProviderWriteReceipt:
        self.calls.append(f"write:{authorization_id}:{transaction_id}")
        return ProviderWriteReceipt(
            operation_id=operation.operation_id,
            provider=operation.provider,
            provider_record_id="provider-record-1",
            idempotency_key=operation.idempotency_key,
            write_digest=operation.payload_digest,
            changed=True,
        )

    def readback(self, receipt: ProviderWriteReceipt) -> ProviderReadbackReceipt:
        self.calls.append(f"readback:{receipt.provider_record_id}")
        return ProviderReadbackReceipt(
            operation_id=receipt.operation_id,
            provider_record_id=receipt.provider_record_id,
            readback_digest=receipt.write_digest,
        )


def test_capture_to_reconciliation_uses_exact_attended_boundaries() -> None:
    capture = CaptureEnvelope(
        source="test",
        content="Deliver the migration. Create the governed Todoist task.",
    )
    graph = DeterministicInputProcessor().process(capture)
    action = next(node for node in graph.nodes if node.execution_candidate)
    operation = PlannedProviderOperation(
        operation_id=action.node_id,
        sequence=0,
        provider="todoist",
        action="create",
        target="#Work/Active Projects",
        payload_digest=sha256_digest({"title": action.title}),
        idempotency_key=f"{capture.correlation_id}:{action.node_id}",
    )
    proposed = ExecutionPlanningService().plan(graph, (operation,))
    authorized = AttendedAuthorizationService().authorize(
        proposed,
        authorization_id="attended-authorization-1",
    )
    port = FakeProviderPort()
    receipt = AttendedExecutionService(port).execute(
        authorized,
        transaction_id="transaction-1",
        write_guard=AllowWriteGuard(),
    )
    reconciliation = CanonicalReconciliationService().reconcile(proposed, receipt)

    assert proposed.contract_id == "atlas.proposed-execution-plan"
    assert authorized.plan_digest == proposed.plan_digest
    assert receipt.provider_writes == 1
    assert reconciliation.complete is True
    assert reconciliation.matched_operation_ids == (action.node_id,)
    assert reconciliation.missing_operation_ids == ()
    assert reconciliation.unexpected_operation_ids == ()
    assert port.calls == [
        "write:attended-authorization-1:transaction-1",
        "readback:provider-record-1",
    ]


def test_blocked_plan_cannot_be_authorized() -> None:
    graph = DeterministicInputProcessor().process(
        CaptureEnvelope(source="test", content="Deliver the migration. Create a task.")
    )
    proposed = ExecutionPlanningService().plan(graph, ())

    assert proposed.blockers
    with pytest.raises(ExecutionBoundaryError, match="blocked"):
        AttendedAuthorizationService().authorize(
            proposed,
            authorization_id="attended-authorization-1",
        )


def test_graph_without_actions_returns_explicit_planning_blocker() -> None:
    graph = DeterministicInputProcessor().process(
        CaptureEnvelope(source="test", content="Review the current implementation status.")
    )

    proposed = ExecutionPlanningService().plan(graph, ())

    assert proposed.operations == ()
    assert proposed.blockers == ("no_execution_candidate_actions",)
