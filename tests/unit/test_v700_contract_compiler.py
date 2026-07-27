from __future__ import annotations

from pathlib import Path

import pytest

from atlas_ros.capabilities.compiler import compile_capability_registry
from atlas_ros.contracts.compiler import (
    ContractCompilationError,
    compile_contract_registry,
)
from atlas_ros.kernel.container import (
    KernelConfig,
    KernelConfigurationError,
    RuntimeKernel,
)


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


def write_contract_catalog(path: Path, body: str | None = None) -> Path:
    path.write_text(
        body
        or (
            "schema_version: '1.0'\n"
            "digest_algorithm: sha256\n"
            "contracts:\n"
            "  - id: atlas.capture-envelope\n"
            "    schema_version: '1.0'\n"
            "    owner: input_processing\n"
            "    schema: schemas/capture/capture-envelope.schema.json\n"
            "    readers: ['1.x']\n"
            "    writer: '1.0'\n"
            "    compatibility: additive_only_within_major\n"
            "lifecycle:\n"
            "  legacy_contracts:\n"
            "    allowed_only_in:\n"
            "      - src/atlas_ros/contracts/migrations\n"
            "      - tests/migration\n"
            "    forbidden_from:\n"
            "      - src/atlas_ros/application\n"
            "      - src/atlas_ros/capabilities\n"
            "      - src/atlas_ros/contracts/execution\n"
            "      - src/atlas_ros/entry_points\n"
            "      - src/atlas_ros/kernel\n"
            "      - src/atlas_ros/policy\n"
            "      - src/atlas_ros/ports\n"
        ),
        encoding="utf-8",
    )
    return path


def test_repository_contract_catalog_compiles() -> None:
    registry = compile_contract_registry(Path("governance/contract-catalog.yaml"))

    assert len(registry.contracts) == 5
    assert registry.require("atlas.authorized-execution-plan").writer == "1.0"
    assert registry.require("atlas.execution-transaction-receipt").migrations == ()
    assert registry.require("atlas.intent-graph").schema_path == (
        "schemas/reasoning/intent-graph.schema.json"
    )
    assert "src/atlas_ros/application" in registry.lifecycle.forbidden_from
    assert "src/atlas_ros/entry_points" in registry.lifecycle.forbidden_from
    assert len(registry.digest) == 64


def test_contract_catalog_rejects_writer_version_mismatch(tmp_path: Path) -> None:
    catalog = write_contract_catalog(tmp_path / "catalog.yaml")
    body = catalog.read_text(encoding="utf-8").replace("writer: '1.0'", "writer: '2.0'")

    with pytest.raises(ContractCompilationError, match="writer"):
        compile_contract_registry(write_contract_catalog(tmp_path / "invalid.yaml", body))


def test_contract_catalog_rejects_unsafe_schema_path(tmp_path: Path) -> None:
    catalog = write_contract_catalog(tmp_path / "catalog.yaml")
    body = catalog.read_text(encoding="utf-8").replace(
        "schemas/capture/capture-envelope.schema.json",
        "../outside.schema.json",
    )

    with pytest.raises(ContractCompilationError, match="schema path"):
        compile_contract_registry(write_contract_catalog(tmp_path / "invalid.yaml", body))


def test_contract_catalog_requires_complete_runtime_prohibitions(tmp_path: Path) -> None:
    catalog = write_contract_catalog(tmp_path / "catalog.yaml")
    body = catalog.read_text(encoding="utf-8").replace(
        "      - src/atlas_ros/entry_points\n",
        "",
    )

    with pytest.raises(ContractCompilationError, match="entry_points"):
        compile_contract_registry(write_contract_catalog(tmp_path / "invalid.yaml", body))


def test_fully_governed_kernel_binds_both_catalogs(tmp_path: Path) -> None:
    contract_path = Path("governance/contract-catalog.yaml")
    capability_path = Path("governance/capability-catalog.yaml")
    contracts = compile_contract_registry(contract_path)
    capabilities = compile_capability_registry(capability_path)
    config = KernelConfig(
        release_version="7.0.0rc1",
        source_commit="a" * 40,
        initializer_version="7.0",
        contract_catalog_digest=contracts.digest,
        capability_catalog_digest=capabilities.digest,
    )

    kernel = RuntimeKernel.compose_fully_governed(
        config,
        [write_policy(tmp_path / "policy.yaml")],
        contract_path,
        capability_path,
        (),
    )

    assert kernel.contract_registry is not None
    assert kernel.capability_registry is not None
    assert kernel.contract_registry.digest == contracts.digest
    assert kernel.capability_registry.digest == capabilities.digest


def test_fully_governed_kernel_rejects_contract_digest_mismatch(tmp_path: Path) -> None:
    capability_path = Path("governance/capability-catalog.yaml")
    capabilities = compile_capability_registry(capability_path)
    config = KernelConfig(
        release_version="7.0.0rc1",
        source_commit="a" * 40,
        initializer_version="7.0",
        contract_catalog_digest="f" * 64,
        capability_catalog_digest=capabilities.digest,
    )

    with pytest.raises(KernelConfigurationError, match="contract catalog digest"):
        RuntimeKernel.compose_fully_governed(
            config,
            [write_policy(tmp_path / "policy.yaml")],
            Path("governance/contract-catalog.yaml"),
            capability_path,
            (),
        )
