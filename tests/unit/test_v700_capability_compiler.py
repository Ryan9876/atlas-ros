from __future__ import annotations

from pathlib import Path

import pytest

from atlas_ros.capabilities.compiler import (
    CapabilityCompilationError,
    compile_capability_registry,
)
from atlas_ros.kernel.container import KernelConfig


def write_catalog(path: Path, body: str | None = None) -> Path:
    repository_root = path.parent
    packages = (
        "input_processing",
        "classification",
        "knowledge_composition",
        "management_reasoning",
        "management_structure",
        "record_routing",
        "execution_planning",
        "framework_composition",
        "minimum_effective_path",
        "execution_intelligence",
        "execution_presentation",
        "scenario_intelligence",
        "decision_support",
        "reconciliation",
    )
    for package in packages:
        package_path = repository_root / f"src/atlas_ros/capabilities/{package}/__init__.py"
        package_path.parent.mkdir(parents=True, exist_ok=True)
        capability_id = "atlas.execution-planning" if package == "execution_planning" else f"atlas.{package.replace('_', '-')}"
        package_path.write_text(f'CAPABILITY_ID = "{capability_id}"\n', encoding="utf-8")
    path.write_text(
        body
        or (
            "schema_version: '1.0'\n"
            "capabilities:\n"
            "  - id: atlas.input-processing\n"
            "    package: capabilities/input_processing\n"
            "    owner: Atlas ROS Core\n"
            "    writes_providers: false\n"
            "    inputs: [CaptureEnvelope]\n"
            "    outputs: [IntentGraph]\n"
            "  - id: atlas.execution-planning\n"
            "    package: capabilities/execution_planning\n"
            "    owner: Atlas ROS Core\n"
            "    writes_providers: false\n"
            "    inputs: [IntentGraph]\n"
            "    outputs: [ProposedExecutionPlan]\n"
            "    sole_planning_authority: true\n"
            "  - id: atlas.reconciliation\n"
            "    package: capabilities/reconciliation\n"
            "    owner: Atlas ROS Core\n"
            "    writes_providers: false\n"
            "    may_create_execution_intent: false\n"
        ),
        encoding="utf-8",
    )
    return path


def kernel_config(capability_digest: str) -> KernelConfig:
    return KernelConfig(
        release_version="7.0.0rc1",
        source_commit="a" * 40,
        initializer_version="7.0",
        contract_catalog_digest="b" * 64,
        capability_catalog_digest=capability_digest,
    )


def test_compiler_builds_digest_bound_immutable_registry(tmp_path: Path) -> None:
    registry = compile_capability_registry(write_catalog(tmp_path / "catalog.yaml"))

    assert registry.planning_authority_id == "atlas.execution-planning"
    assert registry.planning_authority.module_name == (
        "atlas_ros.capabilities.execution_planning"
    )
    assert len(registry.digest) == 64
    assert registry.require("atlas.input-processing").inputs == ("CaptureEnvelope",)
    with pytest.raises(TypeError):
        registry.capabilities["atlas.other"] = registry.planning_authority  # type: ignore[index]


def test_repository_catalog_compiles_with_exact_invariants() -> None:
    registry = compile_capability_registry(Path("governance/capability-catalog.yaml"))

    assert len(registry.capabilities) == 22
    assert registry.planning_authority_id == "atlas.execution-planning"
    assert registry.require("atlas.reconciliation").may_create_execution_intent is False
    assert registry.require("atlas.work-graph-hygiene").may_create_execution_intent is False
    assert registry.require("atlas.command-lifecycle").writes_providers is False
    clarification = registry.require("atlas.context-aware-clarification")
    assert clarification.writes_providers is False
    assert clarification.advisory_only is True
    assert clarification.may_create_execution_intent is False
    assert all(not item.writes_providers for item in registry.capabilities.values())


def test_compiler_rejects_provider_writing_capability(tmp_path: Path) -> None:
    body = write_catalog(tmp_path / "catalog.yaml").read_text(encoding="utf-8")
    body = body.replace("writes_providers: false", "writes_providers: true", 1)

    with pytest.raises(CapabilityCompilationError, match="cannot write providers"):
        compile_capability_registry(write_catalog(tmp_path / "invalid.yaml", body))


def test_compiler_rejects_duplicate_package(tmp_path: Path) -> None:
    body = write_catalog(tmp_path / "catalog.yaml").read_text(encoding="utf-8")
    body = body.replace(
        "package: capabilities/reconciliation",
        "package: capabilities/execution_planning",
    )

    with pytest.raises(CapabilityCompilationError, match="duplicate capability package"):
        compile_capability_registry(write_catalog(tmp_path / "invalid.yaml", body))


def test_compiler_rejects_multiple_planning_authorities(tmp_path: Path) -> None:
    body = write_catalog(tmp_path / "catalog.yaml").read_text(encoding="utf-8")
    body = body.replace(
        "    may_create_execution_intent: false\n",
        "    may_create_execution_intent: false\n"
        "    sole_planning_authority: true\n",
    )

    with pytest.raises(CapabilityCompilationError, match="exactly one planning authority"):
        compile_capability_registry(write_catalog(tmp_path / "invalid.yaml", body))


def test_compiler_rejects_missing_planning_authority(tmp_path: Path) -> None:
    body = write_catalog(tmp_path / "catalog.yaml").read_text(encoding="utf-8")
    body = body.replace("    sole_planning_authority: true\n", "")

    with pytest.raises(CapabilityCompilationError, match="exactly one planning authority"):
        compile_capability_registry(write_catalog(tmp_path / "invalid.yaml", body))


def test_compiler_rejects_unknown_capability_package(tmp_path: Path) -> None:
    body = write_catalog(tmp_path / "catalog.yaml").read_text(encoding="utf-8")
    body = body.replace(
        "package: capabilities/reconciliation",
        "package: capabilities/missing",
    )

    with pytest.raises(CapabilityCompilationError, match="package does not exist"):
        compile_capability_registry(write_catalog(tmp_path / "invalid.yaml", body))


def test_kernel_config_can_bind_compiled_capability_digest(tmp_path: Path) -> None:
    registry = compile_capability_registry(write_catalog(tmp_path / "catalog.yaml"))
    config = kernel_config(registry.digest)

    assert config.capability_catalog_digest == registry.digest
