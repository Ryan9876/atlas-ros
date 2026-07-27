"""Single canonical v7 composition from capture through reconciled execution."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime

from atlas_ros.application.pipeline import (
    CanonicalPipelineError,
    CanonicalPreAuthorizationPipeline,
    CanonicalPreAuthorizationResult,
)
from atlas_ros.application.transaction import (
    GovernedExecutionTransactionService,
    GovernedTransactionResult,
)
from atlas_ros.capabilities.execution_intelligence import (
    ProviderFreeExecutionIntelligenceService,
)
from atlas_ros.capabilities.execution_presentation import (
    HumanReadableExecutionPresentationService,
)
from atlas_ros.capabilities.interfaces import (
    ExecutionIntelligenceResult,
    ExecutionPresentationResult,
)
from atlas_ros.contracts.digests import sha256_digest
from atlas_ros.contracts.execution.pipeline import CaptureEnvelope, PipelineRunEnvelope
from atlas_ros.contracts.execution.transaction import PlannedProviderOperation


@dataclass(frozen=True, slots=True)
class CanonicalAttendedResult:
    """Complete lineage, transaction, intelligence, and presentation evidence."""

    pre_authorization: CanonicalPreAuthorizationResult
    transaction: GovernedTransactionResult
    execution_intelligence: ExecutionIntelligenceResult
    lineage: PipelineRunEnvelope
    presentation: ExecutionPresentationResult


@dataclass(frozen=True, slots=True)
class CanonicalAttendedPipeline:
    """Run the only supported capture-to-reconciled-provider transaction path."""

    pre_authorization: CanonicalPreAuthorizationPipeline
    transaction: GovernedExecutionTransactionService
    intelligence: ProviderFreeExecutionIntelligenceService = (
        ProviderFreeExecutionIntelligenceService()
    )
    presenter: HumanReadableExecutionPresentationService = (
        HumanReadableExecutionPresentationService()
    )

    def process(
        self,
        envelope: CaptureEnvelope,
        *,
        provider_requests: tuple[PlannedProviderOperation, ...],
        authorization_id: str,
        transaction_id: str,
        authorized_at: datetime | None = None,
        framework_rules: tuple[str, ...] = (),
        mandatory_step_ids: tuple[str, ...] = (),
        scenario_ids: tuple[str, ...] = (),
    ) -> CanonicalAttendedResult:
        pre_authorization = self.pre_authorization.process(
            envelope,
            provider_requests=provider_requests,
            framework_rules=framework_rules,
            mandatory_step_ids=mandatory_step_ids,
            scenario_ids=scenario_ids,
        )
        proposed = pre_authorization.state.proposed_plan
        if proposed is None:
            raise CanonicalPipelineError(
                "canonical pre-authorization pipeline did not produce a plan"
            )
        transaction = self.transaction.execute(
            proposed,
            authorization_id=authorization_id,
            transaction_id=transaction_id,
            authorized_at=authorized_at,
        )
        execution_intelligence = self.intelligence.analyze(
            transaction.execution_receipt
        )
        lineage = _complete_lineage(
            pre_authorization.lineage,
            transaction,
            execution_intelligence,
        )
        return CanonicalAttendedResult(
            pre_authorization=pre_authorization,
            transaction=transaction,
            execution_intelligence=execution_intelligence,
            lineage=lineage,
            presentation=self.presenter.render(lineage),
        )


def _complete_lineage(
    lineage: PipelineRunEnvelope,
    transaction: GovernedTransactionResult,
    intelligence: ExecutionIntelligenceResult,
) -> PipelineRunEnvelope:
    receipt = transaction.execution_receipt
    operation_receipts = tuple(
        (
            f"{item.operation_id}:{item.provider}:"
            f"{item.provider_record_id}:{item.write_digest}"
        )
        for item in receipt.operation_receipts
    )
    readbacks = tuple(item.readback_digest for item in receipt.operation_receipts)
    reconciliation_digest = sha256_digest(asdict(transaction.reconciliation))
    return lineage.model_copy(
        update={
            "authorization_id": transaction.authorized_plan.authorization_id,
            "execution_transaction_id": receipt.transaction_id,
            "provider_operation_receipts": operation_receipts,
            "readback_results": readbacks,
            "reconciliation_receipt": reconciliation_digest,
            "warnings": intelligence.warnings,
            "blockers": (),
            "completion_state": "completed",
            "completed_at": receipt.completed_at,
        }
    )


__all__ = ["CanonicalAttendedPipeline", "CanonicalAttendedResult"]
