from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from atlas_ros.capabilities.compiler import (
    CapabilityCompilationError,
    compile_capability_registry,
)
from atlas_ros.kernel.container import (
    KernelConfig,
    KernelConfigurationError,
    RuntimeKernel,
)


def write_catalog(path: Path, body: str | None = None) -> Path:
    text = body or (
        "schema_version: '1.0'\n"
        "capabilities:\n"
        "  - id: atlas.input-processing\n"
        "    package: capabilities/input_processing\n"
        "    owner: Atlas ROS Core\n"
        "    writes_providers: false\n"
        "    inputs: [CaptureEnvelope]\n"
        "    outputs: [CanonicalIntent]\n"
        "  - id: atlas.execution-planning\n"
        "    package: capabilities/execution_planning\n"
        "    owner: Atlas ROS Core\n"
        "    writes_providers: false\n"
        "    sole_planning_authority: true\n"
        "  - id: atlas.reconciliation\n"
        "    package: capabilities/reconciliation\n"
        "    owner: Atlas ROS Core\n"
        "    writes_providers: false\n"
        "    may_create_execution_intent: false\n"
    )
    path.write_text(text, encoding="utf-8")
    loaded = yaml.safe_load(text)
    for item in loaded.get("capabilities", []):
        init_path = path.parent / "src" / "atlas_ros" / item["package"] / "__init__.py"
        init_path.parent.mkdir(parents=True, exist_ok=True)
        init_path.write_text(
            f'CAPABILITY_ID = "{item["id"]}"\n',
            encoding="utf-8",
        )
    return path


def write_policy(path: Path) -> Path:
    path.write_text(
        "schema_version: '1.0'\n"
        "policy_id: atlas.test\n"
        "lifecycle: active\n"
        "rules:\n"
        "  - test_rule\n",
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


def test_compiler_requires_exact_sole_planner(tmp_path: Path) -> None:
    body = write_catalog(tmp_path / "catalog.yaml").read_text(encoding="utf-8")
    body = body.replace("    sole_planning_authority: true\n", "")

    with pytest.raises(CapabilityCompilationError, match="sole planner"):
        compile_capability_registry(write_catalog(tmp_path / "invalid.yaml", body))


def test_compiler_rejects_reconciliation_intent_creation(tmp_path: Path) -> None:
    body = write_catalog(tmp_path / "catalog.yaml").read_text(encoding="utf-8")
    body = body.replace(
        "may_create_execution_intent: false",
        "may_create_execution_intent: true",
    )

    with pytest.raises(CapabilityCompilationError, match="reconciliation"):
        compile_capability_registry(write_catalog(tmp_path / "invalid.yaml", body))


def test_compiler_rejects_advisory_planning_authority(tmp_path: Path) -> None:
    body = write_catalog(tmp_path / "catalog.yaml").read_text(encoding="utf-8")
    body = body.replace(
        "    sole_planning_authority: true\n",
        "    sole_planning_authority: true\n    advisory_only: true\n",
    )

    with pytest.raises(CapabilityCompilationError, match="advisory-only"):
        compile_capability_registry(write_catalog(tmp_path / "invalid.yaml", body))


def test_compiler_rejects_missing_package(tmp_path: Path) -> None:
    catalog = write_catalog(tmp_path / "catalog.yaml")
    missing = tmp_path / "src" / "atlas_ros" / "capabilities" / "input_processing"
    (missing / "__init__.py").unlink()

    with pytest.raises(CapabilityCompilationError, match="package is missing"):
        compile_capability_registry(catalog)


def test_compiler_rejects_package_id_mismatch(tmp_path: Path) -> None:
    catalog = write_catalog(tmp_path / "catalog.yaml")
    init_path = (
        tmp_path
        / "src"
        / "atlas_ros"
        / "capabilities"
        / "input_processing"
        / "__init__.py"
    )
    init_path.write_text('CAPABILITY_ID = "atlas.wrong"\n', encoding="utf-8")

    with pytest.raises(CapabilityCompilationError, match="ID disagrees"):
        compile_capability_registry(catalog)


def test_governed_kernel_binds_compiled_capability_digest(tmp_path: Path) -> None:
    catalog = write_catalog(tmp_path / "catalog.yaml")
    registry = compile_capability_registry(catalog)

    kernel = RuntimeKernel.compose_governed(
        kernel_config(registry.digest),
        [write_policy(tmp_path / "policy.yaml")],
        catalog,
        (),
    )

    assert kernel.capability_registry is not None
    assert kernel.capability_registry.digest == registry.digest
    assert kernel.coordinator.capability_catalog_digest == registry.digest


def test_governed_kernel_rejects_catalog_digest_mismatch(tmp_path: Path) -> None:
    catalog = write_catalog(tmp_path / "catalog.yaml")

    with pytest.raises(KernelConfigurationError, match="digest"):
        RuntimeKernel.compose_governed(
            kernel_config("f" * 64),
            [write_policy(tmp_path / "policy.yaml")],
            catalog,
            (),
        )


def test_capability_package_import_is_lazy() -> None:
    program = """
import sys
import atlas_ros.capabilities
for prefix in (
    'atlas_ros.engines',
    'atlas_ros.orchestration',
    'atlas_ros.planning',
    'atlas_ros.reconciliation',
    'atlas_ros.services',
):
    assert not any(name == prefix or name.startswith(prefix + '.') for name in sys.modules), prefix
"""
    result = subprocess.run(
        [sys.executable, "-c", program],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
