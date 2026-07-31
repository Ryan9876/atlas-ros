from __future__ import annotations

from dataclasses import dataclass

from atlas_ros import contracts
from atlas_ros.reconciliation import service as reconciliation_service

ReconciliationPlan = reconciliation_service.ReconciliationPlan
LegacyReconciliationResult = reconciliation_service.ReconciliationResult
TodoistReconciliationService = reconciliation_service.TodoistReconciliationService
ReconciliationApplyAuthorization = reconciliation_service.ReconciliationApplyAuthorization
CanonicalReconciliationResult = contracts.ReconciliationResult


@dataclass(frozen=True)
class ReconciliationOutcome:
    legacy: LegacyReconciliationResult
    canonical: CanonicalReconciliationResult


class ExecutionReconciliationService(TodoistReconciliationService):
    """Semantic reconciliation boundary for the provider adapters."""

    def apply(
        self,
        plan: ReconciliationPlan,
        *,
        confirmed: bool = False,
        authorization: ReconciliationApplyAuthorization | None = None,
    ) -> LegacyReconciliationResult:
        checkpoint_before = self.state_store.checkpoint()
        result = super().apply(
            plan, confirmed=confirmed, authorization=authorization
        )
        if result.conflicts:
            self.state_store.set_checkpoint(checkpoint_before)
        return result

    def apply_with_contract(
        self,
        plan: ReconciliationPlan,
        *,
        confirmed: bool = False,
    ) -> ReconciliationOutcome:
        result = self.apply(plan, confirmed=confirmed)
        mismatches = tuple(plan.conflicts)
        if result.conflicts and not mismatches:
            mismatches = (f"{result.conflicts} reconciliation conflict(s)",)
        canonical = CanonicalReconciliationResult(
            source_component="services.execution_reconciliation",
            object_id="todoist-notion-reconciliation",
            consistent=result.conflicts == 0,
            mismatches=list(mismatches),
            checkpoint_advanced=result.conflicts == 0,
        )
        return ReconciliationOutcome(legacy=result, canonical=canonical)
