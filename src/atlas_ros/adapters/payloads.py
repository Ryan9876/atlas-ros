"""Ephemeral checksum-bound payload storage for attended provider execution."""

from __future__ import annotations

from dataclasses import dataclass, field

from atlas_ros.contracts.execution.payload import ProviderOperationPayload
from atlas_ros.contracts.execution.transaction import PlannedProviderOperation


class ExecutionPayloadError(RuntimeError):
    """Raised when resolved payload content contradicts an authorized operation."""


@dataclass(slots=True)
class InMemoryExecutionPayloadStore:
    """Retain exact payloads in memory without becoming canonical authority."""

    _payloads: dict[str, ProviderOperationPayload] = field(default_factory=dict)

    def register(self, payload: ProviderOperationPayload) -> None:
        """Bind one immutable payload to its operation ID."""
        existing = self._payloads.get(payload.operation_id)
        if existing is not None and existing != payload:
            raise ExecutionPayloadError(
                "operation ID is already bound to different payload content"
            )
        self._payloads[payload.operation_id] = payload

    def resolve(self, operation: PlannedProviderOperation) -> ProviderOperationPayload:
        """Return exact content only when operation ID and digest both agree."""
        try:
            payload = self._payloads[operation.operation_id]
        except KeyError as error:
            raise ExecutionPayloadError(
                f"no payload is registered for operation: {operation.operation_id}"
            ) from error
        if payload.payload_digest != operation.payload_digest:
            raise ExecutionPayloadError(
                "registered payload digest disagrees with the authorized operation"
            )
        return payload

    def discard(self, operation_id: str) -> None:
        """Remove ephemeral content after governed completion or cancellation."""
        self._payloads.pop(operation_id, None)


__all__ = ["ExecutionPayloadError", "InMemoryExecutionPayloadStore"]
