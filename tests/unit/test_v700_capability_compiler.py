from __future__ import annotations

from pathlib import Path

import pytest

from atlas_ros.capabilities.compiler import (
    CapabilityCompilationError,
    compile_capability_registry,
)


def write_catalog(path: Path, body: str | None = None) -> Path:
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
        ),
        encoding="utf-8",
    )
    return path


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
