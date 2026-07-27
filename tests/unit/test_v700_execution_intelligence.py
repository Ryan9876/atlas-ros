from __future__ import annotations

from atlas_ros.capabilities.execution_intelligence import (
    ProviderFreeExecutionIntelligenceService,
)
from atlas_ros.contracts.execution.transaction import (
    ExecutedOperationReceipt,
    ExecutionTransactionReceipt,
)


def test_execution_intelligence_uses_only_verified_receipt_evidence() -> None:
    receipt = ExecutionTransactionReceipt(
        transaction_id="transaction-1",
        authorization_id="authorization-1",
        plan_digest="a" * 64,
        operation_receipts=(
            ExecutedOperationReceipt(
                operation_id="operation-1",
                provider="todoist",
                provider_record_id="task-1",
                idempotency_key="key-1",
                write_digest="b" * 64,
                readback_digest="b" * 64,
                changed=False,
            ),
        ),
        provider_writes=0,
    )

    result = ProviderFreeExecutionIntelligenceService().analyze(receipt)

    assert result.state == "completed"
    assert result.next_valid_actions == ("reconcile_exact_plan",)
    assert result.evidence_refs == (f"provider:todoist:task-1:{'b' * 64}",)
    assert result.warnings == ("idempotent_no_change:operation-1",)
