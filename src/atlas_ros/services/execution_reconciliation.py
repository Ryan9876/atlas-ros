from __future__ import annotations

from dataclasses import dataclass

from atlas_ros.contracts import ReconciliationResult as CanonicalReconciliationResult
from atlas_ros.workflows.w04_reconciliation import (
    ReconciliationPlan,
    ReconciliationResult as LegacyReconciliationResult,
    TodoistReconciliationService,
)


@dataclass(frozen=True)
class ReconciliationOutcome:
    legacy: LegacyReconciliationResult
    canonical: CanonicalReconciliationResult


class ExecutionReconciliationService(TodoistReconciliationService):
    """Semantic reconciliation boundary preserving the attended W04 behavior."""

    def apply(
        self,
        plan: ReconciliationPlan,
        *,
        confirmed: bool = False,
    ) -> LegacyReconciliationResult:
        checkpoint_before = self.state_store.checkpoint()
        result = super().apply(plan, confirmed=confirmed)
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
