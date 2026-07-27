"""Human-readable provider-free execution presentation for Atlas ROS v7."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from atlas_ros.capabilities.interfaces import ExecutionPresentationResult
from atlas_ros.contracts.digests import sha256_digest
from atlas_ros.contracts.execution.pipeline import PipelineRunEnvelope

CAPABILITY_ID = "atlas.execution-presentation"


class ExecutionPresentationPort(Protocol):
    def render(self, envelope: PipelineRunEnvelope) -> ExecutionPresentationResult: ...


@dataclass(frozen=True, slots=True)
class HumanReadableExecutionPresentationService:
    """Separate executive, technical, warning, and blocker evidence without mutation."""

    capability_id: str = CAPABILITY_ID

    def render(self, envelope: PipelineRunEnvelope) -> ExecutionPresentationResult:
        stage_names = tuple(envelope.stage_digests)
        executive = (
            f"Pipeline {envelope.completion_state}: {len(stage_names)} deterministic stages; "
            f"{len(envelope.blockers)} blockers; {len(envelope.warnings)} warnings."
        )
        technical = (
            f"run={envelope.run_id}; correlation={envelope.correlation_id}; "
            f"release={envelope.release_version}; source={envelope.source_commit}; "
            f"authorization={envelope.authorization_id or 'none'}; "
            f"transaction={envelope.execution_transaction_id or 'none'}; "
            f"stages={','.join(stage_names) or 'none'}; "
            f"blockers={','.join(envelope.blockers) or 'none'}; "
            f"warnings={','.join(envelope.warnings) or 'none'}"
        )
        audit_digest = sha256_digest(
            {
                "executive_summary": executive,
                "technical_summary": technical,
                "run_id": str(envelope.run_id),
                "input_digest": envelope.input_digest,
                "stage_digests": envelope.stage_digests,
            }
        )
        return ExecutionPresentationResult(
            executive_summary=executive,
            technical_summary=technical,
            audit_digest=audit_digest,
        )


__all__ = [
    "CAPABILITY_ID",
    "ExecutionPresentationPort",
    "ExecutionPresentationResult",
    "HumanReadableExecutionPresentationService",
]
