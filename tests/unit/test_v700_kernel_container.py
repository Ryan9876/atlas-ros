from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest

from atlas_ros.capabilities.compiler import compile_capability_registry
from atlas_ros.contracts.execution.pipeline import CaptureEnvelope
from atlas_ros.kernel.container import (
    KernelConfig,
    KernelConfigurationError,
    KernelPermissionError,
    RuntimeKernel,
    RuntimeMode,
)


@dataclass(frozen=True)
class UppercaseStage:
    name: str = "normalize"

    def process(self, value: CaptureEnvelope) -> str:
        return value.content.upper()


def policy_file(path: Path) -> Path:
    path.write_text(
        "schema_version: '1.0'\n"
        "policy_id: atlas.test\n"
        "lifecycle: active\n"
        "rules:\n"
        "  - test_rule\n",
        encoding="utf-8",
    )
    return path


def capability_catalog(path: Path) -> Path:
    path.write_text(
        "schema_version: '1.0'\n"
        "capabilities:\n"
        "  - id: atlas.execution-planning\n"
        "    package: capabilities/execution_planning\n"
        "    owner: Atlas ROS Core\n"
        "    writes_providers: false\n"
        "    sole_planning_authority: true\n"
        "  - id: atlas.reconciliation\n"
        "    package: capabilities/reconciliation\n"
        "    owner: Atlas ROS Core\n"
        "    writes_providers: false\n"
        "    may_create_execution_intent: false\n",
        encoding="utf-8",
    )
    return path


def config(
    *,
    mode: RuntimeMode = RuntimeMode.PRODUCTION,
    capability_digest: str = "c" * 64,
) -> KernelConfig:
    return KernelConfig(
        release_version="7.0.0",
        source_commit="a" * 40,
        initializer_version="7.0",
        contract_catalog_digest="b" * 64,
        capability_catalog_digest=capability_digest,
        mode=mode,
    )


def test_kernel_composes_one_registry_and_canonical_coordinator(tmp_path: Path) -> None:
    kernel = RuntimeKernel.compose(
        config(),
        [policy_file(tmp_path / "policy.yaml")],
        (UppercaseStage(),),
    )
    value, lineage = kernel.coordinator.process(
        CaptureEnvelope(source="test", content="hello")
    )
    assert value == "HELLO"
    assert lineage.policy_registry_digest == kernel.policy_registry.digest


def test_governed_kernel_binds_compiled_capability_registry(tmp_path: Path) -> None:
    catalog = capability_catalog(tmp_path / "capabilities.yaml")
    expected = compile_capability_registry(catalog)
    kernel = RuntimeKernel.compose_governed(
        config(capability_digest=expected.digest),
        [policy_file(tmp_path / "policy.yaml")],
        catalog,
        (UppercaseStage(),),
    )

    assert kernel.capability_registry is not None
    assert kernel.capability_registry.digest == expected.digest
    assert kernel.coordinator.capability_catalog_digest == expected.digest


def test_governed_kernel_rejects_catalog_digest_mismatch(tmp_path: Path) -> None:
    catalog = capability_catalog(tmp_path / "capabilities.yaml")

    with pytest.raises(KernelConfigurationError, match="does not match"):
        RuntimeKernel.compose_governed(
            config(capability_digest="f" * 64),
            [policy_file(tmp_path / "policy.yaml")],
            catalog,
            (),
        )


def test_non_production_kernel_rejects_provider_writes(tmp_path: Path) -> None:
    kernel = RuntimeKernel.compose(
        config(mode=RuntimeMode.SIMULATION),
        [policy_file(tmp_path / "policy.yaml")],
        (),
    )
    with pytest.raises(KernelPermissionError, match="simulation"):
        kernel.require_provider_write_permission("approved")


def test_production_kernel_requires_explicit_authorization(tmp_path: Path) -> None:
    kernel = RuntimeKernel.compose(config(), [policy_file(tmp_path / "policy.yaml")], ())
    with pytest.raises(KernelPermissionError, match="authorization"):
        kernel.require_provider_write_permission(None)
    kernel.require_provider_write_permission("approved")
