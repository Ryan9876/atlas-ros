"""Governed attended execution transaction coordination."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from atlas_ros.application.execution import (
    AttendedAuthorizationService,
    AttendedExecutionService,
    ExecutionBoundaryError,
)
from atlas_ros.capabilities.interfaces import ProposedExecutionPlan, ReconciliationResult
from atlas_ros.capabilities.reconciliation import CanonicalReconciliationService
from atlas_ros.contracts.execution.transaction import (
    AuthorizedExecutionPlan,
    ExecutionTransactionReceipt,
)
from atlas_ros.kernel.container import RuntimeKernel


@dataclass(frozen=True, slots=True)
class GovernedTransactionResult:
    """Bound authorization, execution, and reconciliation evidence."""

    authorized_plan: AuthorizedExecutionPlan
    execution_receipt: ExecutionTransactionReceipt
    reconciliation: ReconciliationResult


@dataclass(frozen=True, slots=True)
class GovernedExecutionTransactionService:
    """Run the only supported attended plan-to-readback transaction sequence."""

    kernel: RuntimeKernel
    executor: AttendedExecutionService
    authorizer: AttendedAuthorizationService = AttendedAuthorizationService()
    reconciler: CanonicalReconciliationService = CanonicalReconciliationService()

    def execute(
        self,
        proposed_plan: ProposedExecutionPlan,
        *,
        authorization_id: str,
        transaction_id: str,
        authorized_at: datetime | None = None,
    ) -> GovernedTransactionResult:
        self.kernel.require_provider_write_permission(authorization_id)
        authorized = self.authorizer.authorize(
            proposed_plan,
            authorization_id=authorization_id,
            authorized_at=authorized_at,
        )
        receipt = self.executor.execute(authorized, transaction_id=transaction_id)
        reconciliation = self.reconciler.reconcile(proposed_plan, receipt)
        if not reconciliation.complete:
            raise ExecutionBoundaryError(
                "provider transaction completed readback but reconciliation is incomplete"
            )
        return GovernedTransactionResult(
            authorized_plan=authorized,
            execution_receipt=receipt,
            reconciliation=reconciliation,
        )
