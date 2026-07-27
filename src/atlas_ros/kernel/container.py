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
from atlas_ros.capabilities.compiler import compile_capability_registry
from atlas_ros.capabilities.registry import CapabilityRegistry
from atlas_ros.contracts.compiler import compile_contract_registry
from atlas_ros.contracts.registry import ContractRegistry
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


class KernelConfigurationError(ValueError):
    """Raised when compiled governance does not match the bound kernel identity."""


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
    """Owns immutable registries and the sole canonical coordinator."""

    config: KernelConfig
    policy_registry: PolicyRegistry
    coordinator: CanonicalProcessingCoordinator
    contract_registry: ContractRegistry | None = None
    capability_registry: CapabilityRegistry | None = None

    @classmethod
    def compose(
        cls,
        config: KernelConfig,
        policy_paths: Iterable[Path],
        stages: tuple[ProcessingStage, ...],
    ) -> RuntimeKernel:
        """Compose a compatibility kernel when catalogs are bound externally."""
        policy_registry = compile_policy_registry(policy_paths)
        coordinator = _coordinator(config, policy_registry, stages)
        return cls(config=config, policy_registry=policy_registry, coordinator=coordinator)

    @classmethod
    def compose_governed(
        cls,
        config: KernelConfig,
        policy_paths: Iterable[Path],
        contract_catalog_path: Path,
        capability_catalog_path: Path,
        stages: tuple[ProcessingStage, ...],
    ) -> RuntimeKernel:
        """Compile and bind canonical governance at composition time."""
        policy_registry = compile_policy_registry(policy_paths)
        contract_registry = compile_contract_registry(contract_catalog_path)
        capability_registry = compile_capability_registry(capability_catalog_path)
        if contract_registry.digest != config.contract_catalog_digest:
            raise KernelConfigurationError(
                "compiled contract catalog digest does not match kernel configuration"
            )
        if capability_registry.digest != config.capability_catalog_digest:
            raise KernelConfigurationError(
                "compiled capability catalog digest does not match kernel configuration"
            )
        coordinator = _coordinator(config, policy_registry, stages)
        return cls(
            config=config,
            policy_registry=policy_registry,
            coordinator=coordinator,
            contract_registry=contract_registry,
            capability_registry=capability_registry,
        )

    def require_provider_write_permission(self, authorization_id: str | None) -> None:
        """Enforce that only an explicitly authorized production runtime can write."""
        if self.config.mode is not RuntimeMode.PRODUCTION:
            raise KernelPermissionError(
                f"{self.config.mode.value} mode never permits provider writes"
            )
        if not authorization_id:
            raise KernelPermissionError("provider writes require an authorization ID")


def _coordinator(
    config: KernelConfig,
    policy_registry: PolicyRegistry,
    stages: tuple[ProcessingStage, ...],
) -> CanonicalProcessingCoordinator:
    return CanonicalProcessingCoordinator(
        release_version=config.release_version,
        source_commit=config.source_commit,
        initializer_version=config.initializer_version,
        contract_catalog_digest=config.contract_catalog_digest,
        policy_registry_digest=policy_registry.digest,
        capability_catalog_digest=config.capability_catalog_digest,
        stages=stages,
    )
