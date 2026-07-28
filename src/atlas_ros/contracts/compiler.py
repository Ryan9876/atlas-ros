"""Fail-closed compiler for the canonical contract catalog."""

from __future__ import annotations

import re
from collections.abc import Mapping
from pathlib import Path, PurePosixPath
from typing import Any, cast

import yaml

from atlas_ros.contracts.digests import sha256_digest
from atlas_ros.contracts.registry import (
    ContractDescriptor,
    ContractRegistry,
    LegacyContractBoundary,
)

_VERSION = re.compile(r"^[0-9]+\.[0-9]+$")
_READER = re.compile(r"^[0-9]+\.x$")
_COMPATIBILITY = {"additive_only_within_major", "explicit_migration"}
_REQUIRED_LEGACY_PROHIBITIONS = {
    "src/atlas_ros/application",
    "src/atlas_ros/capabilities",
    "src/atlas_ros/contracts/execution",
    "src/atlas_ros/entry_points",
    "src/atlas_ros/kernel",
    "src/atlas_ros/policy",
    "src/atlas_ros/ports",
}


class ContractCompilationError(ValueError):
    """Raised when the canonical contract catalog is invalid or ambiguous."""


def compile_contract_registry(
    path: Path,
    *,
    repository_root: Path | None = None,
) -> ContractRegistry:
    """Compile one canonical YAML contract catalog into an immutable registry."""
    try:
        loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    except OSError as error:
        raise ContractCompilationError(f"cannot read contract catalog: {path}") from error
    except yaml.YAMLError as error:
        raise ContractCompilationError(f"invalid contract catalog YAML: {path}") from error
    if not isinstance(loaded, Mapping):
        raise ContractCompilationError("contract catalog must be a mapping")
    payload = cast(dict[str, Any], dict(loaded))
    expected = {"schema_version", "digest_algorithm", "contracts", "lifecycle"}
    if set(payload) != expected:
        raise ContractCompilationError("contract catalog has unsupported or missing fields")
    if payload["schema_version"] != "1.0":
        raise ContractCompilationError("unsupported contract catalog schema version")
    if payload["digest_algorithm"] != "sha256":
        raise ContractCompilationError("contract catalog digest algorithm must be sha256")
    entries = payload["contracts"]
    if not isinstance(entries, list) or not entries:
        raise ContractCompilationError("contract catalog must contain contracts")

    compiled: dict[str, ContractDescriptor] = {}
    canonical_entries: list[dict[str, Any]] = []
    for raw in entries:
        descriptor, canonical = _compile_entry(raw)
        if descriptor.contract_id in compiled:
            raise ContractCompilationError(
                f"duplicate contract ID: {descriptor.contract_id}"
            )
        compiled[descriptor.contract_id] = descriptor
        canonical_entries.append(canonical)

    root = _resolve_repository_root(path, repository_root)
    _validate_catalog_assets(compiled, root)
    lifecycle, canonical_lifecycle = _compile_lifecycle(payload["lifecycle"])
    canonical_catalog = {
        "schema_version": "1.0",
        "digest_algorithm": "sha256",
        "contracts": canonical_entries,
        "lifecycle": canonical_lifecycle,
    }
    try:
        return ContractRegistry.create(
            compiled,
            lifecycle,
            sha256_digest(canonical_catalog),
        )
    except ValueError as error:
        raise ContractCompilationError(str(error)) from error


def _compile_entry(raw: Any) -> tuple[ContractDescriptor, dict[str, Any]]:
    if not isinstance(raw, Mapping):
        raise ContractCompilationError("each contract must be a mapping")
    payload = cast(dict[str, Any], dict(raw))
    allowed = {
        "id",
        "schema_version",
        "owner",
        "schema",
        "readers",
        "writer",
        "migrations",
        "compatibility",
    }
    required = allowed - {"migrations"}
    if not required.issubset(payload) or not set(payload).issubset(allowed):
        raise ContractCompilationError("contract has unsupported or missing fields")

    contract_id = _required_string(payload, "id")
    schema_version = _required_string(payload, "schema_version")
    owner = _required_string(payload, "owner")
    schema_path = _required_string(payload, "schema")
    writer = _required_string(payload, "writer")
    compatibility = _required_string(payload, "compatibility")
    readers = _string_tuple(payload["readers"], "readers", contract_id)
    migrations = _string_tuple(payload.get("migrations", []), "migrations", contract_id)

    if not _VERSION.fullmatch(schema_version):
        raise ContractCompilationError(
            f"invalid contract schema version: {contract_id} {schema_version}"
        )
    if writer != schema_version:
        raise ContractCompilationError(
            f"contract writer must equal schema version: {contract_id}"
        )
    expected_reader = schema_version.split(".", 1)[0] + ".x"
    if expected_reader not in readers or not all(_READER.fullmatch(item) for item in readers):
        raise ContractCompilationError(
            f"contract readers do not cover the writer major version: {contract_id}"
        )
    if compatibility not in _COMPATIBILITY:
        raise ContractCompilationError(
            f"unsupported contract compatibility mode: {contract_id}"
        )
    _validate_schema_path(schema_path, contract_id)
    for migration in migrations:
        _validate_migration_path(migration, contract_id)
    if compatibility == "explicit_migration" and schema_version != "1.0" and not migrations:
        raise ContractCompilationError(
            f"versioned explicit-migration contract requires a migration: {contract_id}"
        )

    canonical: dict[str, Any] = {
        "id": contract_id,
        "schema_version": schema_version,
        "owner": owner,
        "schema": schema_path,
        "readers": list(readers),
        "writer": writer,
    }
    if migrations:
        canonical["migrations"] = list(migrations)
    canonical["compatibility"] = compatibility
    descriptor = ContractDescriptor(
        contract_id=contract_id,
        schema_version=schema_version,
        owner=owner,
        schema_path=schema_path,
        readers=readers,
        writer=writer,
        migrations=migrations,
        compatibility=compatibility,
        digest=sha256_digest(canonical),
    )
    return descriptor, canonical


def _compile_lifecycle(raw: Any) -> tuple[LegacyContractBoundary, dict[str, Any]]:
    if not isinstance(raw, Mapping) or set(raw) != {"legacy_contracts"}:
        raise ContractCompilationError("contract lifecycle must define legacy_contracts")
    legacy = raw["legacy_contracts"]
    if not isinstance(legacy, Mapping):
        raise ContractCompilationError("legacy_contracts must be a mapping")
    if set(legacy) != {"allowed_only_in", "forbidden_from"}:
        raise ContractCompilationError("legacy contract boundary fields are incomplete")
    allowed = _string_tuple(legacy["allowed_only_in"], "allowed_only_in", "lifecycle")
    forbidden = _string_tuple(legacy["forbidden_from"], "forbidden_from", "lifecycle")
    if "src/atlas_ros/contracts/migrations" not in allowed:
        raise ContractCompilationError("legacy contracts must be limited to migrations")
    if not _REQUIRED_LEGACY_PROHIBITIONS.issubset(forbidden):
        missing = sorted(_REQUIRED_LEGACY_PROHIBITIONS - set(forbidden))
        raise ContractCompilationError(
            "legacy contracts are not forbidden from runtime paths: " + ", ".join(missing)
        )
    boundary = LegacyContractBoundary(allowed_only_in=allowed, forbidden_from=forbidden)
    return boundary, {
        "legacy_contracts": {
            "allowed_only_in": list(allowed),
            "forbidden_from": list(forbidden),
        }
    }


def _required_string(payload: Mapping[str, Any], field: str) -> str:
    value = payload.get(field)
    if not isinstance(value, str) or not value:
        raise ContractCompilationError(f"contract {field} must be a non-empty string")
    return value


def _string_tuple(value: Any, field: str, contract_id: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not all(
        isinstance(item, str) and item for item in value
    ):
        raise ContractCompilationError(
            f"contract {field} must be a list of strings: {contract_id}"
        )
    if len(set(value)) != len(value):
        raise ContractCompilationError(
            f"contract {field} contains duplicates: {contract_id}"
        )
    return tuple(value)


def _validate_schema_path(path_value: str, contract_id: str) -> None:
    path = PurePosixPath(path_value)
    if path.is_absolute() or ".." in path.parts or not path_value.startswith("schemas/"):
        raise ContractCompilationError(
            f"invalid schema path for {contract_id}: {path_value}"
        )


def _validate_migration_path(path_value: str, contract_id: str) -> None:
    path = PurePosixPath(path_value)
    prefix = "src/atlas_ros/contracts/migrations/"
    if path.is_absolute() or ".." in path.parts or not path_value.startswith(prefix):
        raise ContractCompilationError(
            f"invalid migration path for {contract_id}: {path_value}"
        )


def _resolve_repository_root(path: Path, repository_root: Path | None) -> Path:
    if repository_root is not None:
        root = repository_root.resolve()
        if not root.is_dir():
            raise ContractCompilationError(f"repository root is not a directory: {root}")
        return root
    resolved = path.resolve()
    for candidate in (resolved.parent, *resolved.parents):
        if (candidate / "pyproject.toml").is_file():
            return candidate
    raise ContractCompilationError(
        "repository root could not be resolved; pass repository_root explicitly"
    )


def _validate_catalog_assets(
    contracts: Mapping[str, ContractDescriptor],
    repository_root: Path,
) -> None:
    for descriptor in contracts.values():
        schema = repository_root / descriptor.schema_path
        if not schema.is_file():
            raise ContractCompilationError(
                f"contract schema asset does not exist: {descriptor.schema_path}"
            )
        for migration_path in descriptor.migrations:
            migration = repository_root / migration_path
            if not migration.is_file():
                raise ContractCompilationError(
                    f"contract migration asset does not exist: {migration_path}"
                )
