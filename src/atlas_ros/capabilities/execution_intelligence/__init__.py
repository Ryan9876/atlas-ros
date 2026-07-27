"""Provider-free execution intelligence for Atlas ROS v7."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from atlas_ros.capabilities.interfaces import ExecutionIntelligenceResult
from atlas_ros.contracts.execution.transaction import ExecutionTransactionReceipt

CAPABILITY_ID = "atlas.execution-intelligence"


class ExecutionIntelligencePort(Protocol):
    def analyze(
        self,
        receipt: ExecutionTransactionReceipt,
    ) -> ExecutionIntelligenceResult: ...


@dataclass(frozen=True, slots=True)
class ProviderFreeExecutionIntelligenceService:
    """Explain completed receipt state without mutating providers or records."""

    capability_id: str = CAPABILITY_ID

    def analyze(
        self,
        receipt: ExecutionTransactionReceipt,
    ) -> ExecutionIntelligenceResult:
        evidence = tuple(
            f"provider:{item.provider}:{item.provider_record_id}:{item.readback_digest}"
            for item in receipt.operation_receipts
        )
        warnings = tuple(
            f"idempotent_no_change:{item.operation_id}"
            for item in receipt.operation_receipts
            if not item.changed
        )
        return ExecutionIntelligenceResult(
            state=receipt.completion_state,
            next_valid_actions=("reconcile_exact_plan",),
            evidence_refs=evidence,
            warnings=warnings,
        )


__all__ = [
    "CAPABILITY_ID",
    "ExecutionIntelligencePort",
    "ExecutionIntelligenceResult",
    "ProviderFreeExecutionIntelligenceService",
]
