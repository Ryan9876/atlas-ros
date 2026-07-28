"""Canonical reconciliation that verifies execution without creating new intent."""

from __future__ import annotations

from dataclasses import dataclass

from atlas_ros.capabilities.interfaces import ReconciliationResult
from atlas_ros.contracts.execution.transaction import (
    ExecutionTransactionReceipt,
    ProposedExecutionPlan,
)

CAPABILITY_ID = "atlas.reconciliation"


@dataclass(frozen=True, slots=True)
class CanonicalReconciliationService:
    """Compare the exact proposed plan with provider readback receipts."""

    capability_id: str = CAPABILITY_ID

    def reconcile(
        self,
        plan: ProposedExecutionPlan,
        receipt: ExecutionTransactionReceipt,
    ) -> ReconciliationResult:
        if receipt.plan_digest != plan.plan_digest:
            raise ValueError("execution receipt references a different plan digest")
        planned = tuple(item.operation_id for item in plan.operations)
        completed = tuple(item.operation_id for item in receipt.operation_receipts)
        planned_set = set(planned)
        completed_set = set(completed)
        matched = tuple(item for item in planned if item in completed_set)
        missing = tuple(item for item in planned if item not in completed_set)
        unexpected = tuple(item for item in completed if item not in planned_set)
        conflicts = tuple(
            f"readback_mismatch:{item.operation_id}"
            for item in receipt.operation_receipts
            if item.write_digest != item.readback_digest
        )
        return ReconciliationResult(
            transaction_id=receipt.transaction_id,
            matched_operation_ids=matched,
            missing_operation_ids=missing,
            unexpected_operation_ids=unexpected,
            conflicts=conflicts,
            complete=not missing and not unexpected and not conflicts,
        )


__all__ = ["CAPABILITY_ID", "CanonicalReconciliationService"]
