"""The sole supported production input-to-output coordinator."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from atlas_ros.contracts.execution.pipeline import CaptureEnvelope, PipelineRunEnvelope
from atlas_ros.kernel.digests import sha256_digest


class ProcessingStage(Protocol):
    """A deterministic provider-neutral stage in the canonical pipeline."""

    name: str

    def process(self, value: Any) -> Any: ...


@dataclass(frozen=True)
class CanonicalProcessingCoordinator:
    """Runs every supplied stage once, records deterministic lineage, and never writes providers."""

    release_version: str
    source_commit: str
    initializer_version: str
    contract_catalog_digest: str
    policy_registry_digest: str
    capability_catalog_digest: str
    stages: tuple[ProcessingStage, ...]

    def process(self, envelope: CaptureEnvelope) -> tuple[Any, PipelineRunEnvelope]:
        value: Any = envelope
        digests: dict[str, str] = {}
        for stage in self.stages:
            value = stage.process(value)
            digests[stage.name] = sha256_digest(self._digestable(value))
        lineage = PipelineRunEnvelope(
            correlation_id=envelope.correlation_id,
            release_version=self.release_version,
            source_commit=self.source_commit,
            initializer_version=self.initializer_version,
            contract_catalog_digest=self.contract_catalog_digest,
            policy_registry_digest=self.policy_registry_digest,
            capability_catalog_digest=self.capability_catalog_digest,
            input_digest=envelope.input_digest,
            stage_digests=digests,
        )
        return value, lineage

    @staticmethod
    def _digestable(value: Any) -> Any:
        model_dump = getattr(value, "model_dump", None)
        if callable(model_dump):
            return model_dump(mode="json")
        if isinstance(value, str | int | float | bool | type(None) | list | tuple | dict):
            return value
        raise TypeError(f"canonical stage returned non-digestable value: {type(value).__name__}")
