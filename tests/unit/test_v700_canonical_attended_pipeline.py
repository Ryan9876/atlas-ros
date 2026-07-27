from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pytest

from atlas_ros.application.attended_pipeline import CanonicalAttendedPipeline
from atlas_ros.application.canonical_processing import CanonicalProcessingCoordinator
from atlas_ros.application.execution import AttendedExecutionService, ExecutionBoundaryError
from atlas_ros.application.pipeline import (
    CanonicalPreAuthorizationPipeline,
    canonical_pre_authorization_stages,
)
from atlas_ros.application.transaction import GovernedExecutionTransactionService
from atlas_ros.capabilities.input_processing import DeterministicInputProcessor
from atlas_ros.contracts.digests import sha256_digest
from atlas_ros.contracts.execution.pipeline import CaptureEnvelope
from atlas_ros.contracts.execution.transaction import (
    PlannedProviderOperation,
    ProviderReadbackReceipt,
    ProviderWriteReceipt,
)
from atlas_ros.kernel.container import (
    KernelConfig,
    KernelPermissionError,
    RuntimeKernel,
    RuntimeMode,
)


@dataclass
class FakeProvider:
    calls: list[str] = field(default_factory=list)

    def write(
        self,
        operation: PlannedProviderOperation,
        *,
        authorization_id: str,
        transaction_id: str,
    ) -> ProviderWriteReceipt:
        self.calls.append(f"write:{operation.operation_id}")
        return ProviderWriteReceipt(
            operation_id=operation.operation_id,
            provider=operation.provider,
            provider_record_id="task-1",
            idempotency_key=operation.idempotency_key,
            write_digest=operation.payload_digest,
            changed=True,
        )

    def readback(self, receipt: ProviderWriteReceipt) -> ProviderReadbackReceipt:
        self.calls.append(f"readback:{receipt.operation_id}")
        return ProviderReadbackReceipt(
            operation_id=receipt.operation_id,
            provider_record_id=receipt.provider_record_id,
            readback_digest=receipt.write_digest,
        )


def policy(path: Path) -> Path:
    path.write_text(
        "schema_version: '1.0'\n"
        "policy_id: atlas.test\n"
        "lifecycle: active\n"
        "rules:\n"
        "  - test_rule\n",
        encoding="utf-8",
    )
    return path


def kernel(tmp_path: Path, mode: RuntimeMode = RuntimeMode.PRODUCTION) -> RuntimeKernel:
    return RuntimeKernel.compose(
        KernelConfig(
            release_version="7.0.0rc1",
            source_commit="a" * 40,
            initializer_version="7.0",
            contract_catalog_digest="b" * 64,
            capability_catalog_digest="c" * 64,
            mode=mode,
        ),
        [policy(tmp_path / "policy.yaml")],
        (),
    )


def envelope() -> CaptureEnvelope:
    return CaptureEnvelope(
        source="test",
        content=(
            "Complete the governed migration. "
            "Create the exact Todoist checkpoint. "
            "Never execute without attended authorization."
        ),
    )


def operation(capture: CaptureEnvelope) -> PlannedProviderOperation:
    graph = DeterministicInputProcessor().process(capture)
    action = next(node for node in graph.nodes if node.execution_candidate)
    return PlannedProviderOperation(
        operation_id=action.node_id,
        sequence=0,
        provider="todoist",
        action="create",
        target="Work/Active Projects",
        payload_digest=sha256_digest({"title": action.title}),
        idempotency_key=f"{capture.correlation_id}:{action.node_id}",
    )


def pipeline(
    tmp_path: Path,
    provider: FakeProvider,
    mode: RuntimeMode,
) -> CanonicalAttendedPipeline:
    pre_authorization = CanonicalPreAuthorizationPipeline(
        CanonicalProcessingCoordinator(
            release_version="7.0.0rc1",
            source_commit="a" * 40,
            initializer_version="7.0",
            contract_catalog_digest="b" * 64,
            policy_registry_digest="d" * 64,
            capability_catalog_digest="c" * 64,
            stages=canonical_pre_authorization_stages(),
        )
    )
    governed_transaction = GovernedExecutionTransactionService(
        kernel(tmp_path, mode),
        AttendedExecutionService(provider),
    )
    return CanonicalAttendedPipeline(pre_authorization, governed_transaction)


def test_canonical_attended_pipeline_binds_all_execution_evidence(tmp_path: Path) -> None:
    capture = envelope()
    provider = FakeProvider()

    result = pipeline(tmp_path, provider, RuntimeMode.PRODUCTION).process(
        capture,
        provider_requests=(operation(capture),),
        authorization_id="authorization-1",
        transaction_id="transaction-1",
        framework_rules=("attended_only", "readback_required"),
    )

    assert result.transaction.reconciliation.complete is True
    assert result.lineage.authorization_id == "authorization-1"
    assert result.lineage.execution_transaction_id == "transaction-1"
    assert len(result.lineage.provider_operation_receipts) == 1
    assert len(result.lineage.readback_results) == 1
    assert result.lineage.reconciliation_receipt is not None
    assert result.lineage.completed_at is not None
    assert "transaction=transaction-1" in result.presentation.technical_summary
    assert provider.calls == [
        f"write:{operation(capture).operation_id}",
        f"readback:{operation(capture).operation_id}",
    ]


def test_simulation_mode_blocks_before_provider_access(tmp_path: Path) -> None:
    capture = envelope()
    provider = FakeProvider()

    with pytest.raises(KernelPermissionError, match="never permits provider writes"):
        pipeline(tmp_path, provider, RuntimeMode.SIMULATION).process(
            capture,
            provider_requests=(operation(capture),),
            authorization_id="authorization-1",
            transaction_id="transaction-1",
        )

    assert provider.calls == []


def test_blocked_pre_authorization_plan_never_reaches_provider(tmp_path: Path) -> None:
    provider = FakeProvider()

    with pytest.raises(ExecutionBoundaryError, match="blocked"):
        pipeline(tmp_path, provider, RuntimeMode.PRODUCTION).process(
            envelope(),
            provider_requests=(),
            authorization_id="authorization-1",
            transaction_id="transaction-1",
        )

    assert provider.calls == []
