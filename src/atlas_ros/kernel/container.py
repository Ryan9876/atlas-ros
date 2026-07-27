"""Runtime composition root for the canonical Atlas ROS pipeline."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from atlas_ros.application.canonical_processing import (
    CanonicalProcessingCoordinator,
    ProcessingStage,
)
from atlas_ros.policy.compiler import compile_policy_registry
from atlas_ros.policy.registry import PolicyRegistry


class RuntimeMode(StrEnum):
    PRODUCTION = "production"
    SIMULATION = "simulation"
    EVALUATION = "evaluation"
    MIGRATION = "migration"
    RESTORATION = "restoration"


class KernelPermissionError(PermissionError):
    """Raised when a runtime mode attempts an operation outside its boundary."""


@dataclass(frozen=True)
class KernelConfig:
    release_version: str
    source_commit: str
    initializer_version: str
    contract_catalog_digest: str
    capability_catalog_digest: str
    mode: RuntimeMode = RuntimeMode.PRODUCTION


@dataclass(frozen=True)
class RuntimeKernel:
    """Owns the immutable registry and the sole canonical coordinator."""

    config: KernelConfig
    policy_registry: PolicyRegistry
    coordinator: CanonicalProcessingCoordinator

    @classmethod
    def compose(
        cls,
        config: KernelConfig,
        policy_paths: Iterable[Path],
        stages: tuple[ProcessingStage, ...],
    ) -> RuntimeKernel:
        policy_registry = compile_policy_registry(policy_paths)
        coordinator = CanonicalProcessingCoordinator(
            release_version=config.release_version,
            source_commit=config.source_commit,
            initializer_version=config.initializer_version,
            contract_catalog_digest=config.contract_catalog_digest,
            policy_registry_digest=policy_registry.digest,
            capability_catalog_digest=config.capability_catalog_digest,
            stages=stages,
        )
        return cls(config=config, policy_registry=policy_registry, coordinator=coordinator)

    def require_provider_write_permission(self, authorization_id: str | None) -> None:
        """Enforce that only an explicitly authorized production runtime can write."""
        if self.config.mode is not RuntimeMode.PRODUCTION:
            raise KernelPermissionError(
                f"{self.config.mode.value} mode never permits provider writes"
            )
        if not authorization_id:
            raise KernelPermissionError("provider writes require an authorization ID")
