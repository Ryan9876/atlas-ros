"""Fail-closed compiler for the canonical capability catalog."""

from __future__ import annotations

import ast
from collections.abc import Mapping
from pathlib import Path, PurePosixPath
from typing import Any, cast

import yaml

from atlas_ros.capabilities.registry import CapabilityDescriptor, CapabilityRegistry
from atlas_ros.contracts.digests import sha256_digest


class CapabilityCompilationError(ValueError):
    """Raised when the canonical capability catalog is invalid or ambiguous."""


def compile_capability_registry(
    path: Path,
    *,
    repository_root: Path | None = None,
) -> CapabilityRegistry:
    """Compile YAML and bind every descriptor to a real capability package."""
    try:
        loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    except OSError as error:
        raise CapabilityCompilationError(f"cannot read capability catalog: {path}") from error
    except yaml.YAMLError as error:
        raise CapabilityCompilationError(f"invalid capability catalog YAML: {path}") from error
    if not isinstance(loaded, Mapping):
        raise CapabilityCompilationError("capability catalog must be a mapping")
    payload = cast(dict[str, Any], dict(loaded))
    if set(payload) != {"schema_version", "capabilities"}:
        raise CapabilityCompilationError("capability catalog has unsupported or missing fields")
    if payload["schema_version"] != "1.0":
        raise CapabilityCompilationError("unsupported capability catalog schema version")
    entries = payload["capabilities"]
    if not isinstance(entries, list) or not entries:
        raise CapabilityCompilationError("capability catalog must contain capabilities")

    compiled: dict[str, CapabilityDescriptor] = {}
    packages: set[str] = set()
    canonical_entries: list[dict[str, Any]] = []
    for raw in entries:
        descriptor, canonical = _compile_entry(raw)
        if descriptor.capability_id in compiled:
            raise CapabilityCompilationError(
                f"duplicate capability ID: {descriptor.capability_id}"
            )
        if descriptor.package in packages:
            raise CapabilityCompilationError(
                f"duplicate capability package: {descriptor.package}"
            )
        compiled[descriptor.capability_id] = descriptor
        packages.add(descriptor.package)
        canonical_entries.append(canonical)

    if "atlas.reconciliation" not in compiled:
        raise CapabilityCompilationError("reconciliation capability is required")
    if compiled["atlas.reconciliation"].may_create_execution_intent is not False:
        raise CapabilityCompilationError(
            "reconciliation must explicitly forbid creating execution intent"
        )
    catalog_digest = sha256_digest(
        {"schema_version": "1.0", "capabilities": canonical_entries}
    )
    try:
        registry = CapabilityRegistry.create(compiled, catalog_digest)
    except ValueError as error:
        raise CapabilityCompilationError(str(error)) from error

    root = repository_root or _repository_root(path)
    for descriptor in registry.capabilities.values():
        _validate_package_implementation(root, descriptor)
    return registry


def _compile_entry(raw: Any) -> tuple[CapabilityDescriptor, dict[str, Any]]:
    if not isinstance(raw, Mapping):
        raise CapabilityCompilationError("each capability must be a mapping")
    payload = cast(dict[str, Any], dict(raw))
    allowed = {
        "id",
        "package",
        "owner",
        "writes_providers",
        "inputs",
        "outputs",
        "sole_planning_authority",
        "advisory_only",
        "may_create_execution_intent",
    }
    required = {"id", "package", "owner", "writes_providers"}
    if not required.issubset(payload) or not set(payload).issubset(allowed):
        raise CapabilityCompilationError("capability has unsupported or missing fields")

    capability_id = _required_string(payload, "id")
    package = _required_string(payload, "package")
    owner = _required_string(payload, "owner")
    writes_providers = payload["writes_providers"]
    if not isinstance(writes_providers, bool):
        raise CapabilityCompilationError(
            f"writes_providers must be boolean: {capability_id}"
        )
    if writes_providers:
        raise CapabilityCompilationError(
            f"capability cannot write providers directly: {capability_id}"
        )
    _validate_package(package, capability_id)

    inputs = _string_tuple(payload.get("inputs", []), "inputs", capability_id)
    outputs = _string_tuple(payload.get("outputs", []), "outputs", capability_id)
    sole_planning_authority = _optional_bool(
        payload, "sole_planning_authority", capability_id, default=False
    )
    advisory_only = _optional_bool(payload, "advisory_only", capability_id, default=False)
    may_create_execution_intent = _nullable_bool(
        payload, "may_create_execution_intent", capability_id
    )
    canonical: dict[str, Any] = {
        "id": capability_id,
        "package": package,
        "owner": owner,
        "writes_providers": writes_providers,
    }
    if inputs:
        canonical["inputs"] = list(inputs)
    if outputs:
        canonical["outputs"] = list(outputs)
    if sole_planning_authority:
        canonical["sole_planning_authority"] = True
    if advisory_only:
        canonical["advisory_only"] = True
    if may_create_execution_intent is not None:
        canonical["may_create_execution_intent"] = may_create_execution_intent

    descriptor = CapabilityDescriptor(
        capability_id=capability_id,
        package=package,
        owner=owner,
        writes_providers=writes_providers,
        inputs=inputs,
        outputs=outputs,
        sole_planning_authority=sole_planning_authority,
        advisory_only=advisory_only,
        may_create_execution_intent=may_create_execution_intent,
        digest=sha256_digest(canonical),
    )
    return descriptor, canonical


def _required_string(payload: Mapping[str, Any], field: str) -> str:
    value = payload.get(field)
    if not isinstance(value, str) or not value:
        raise CapabilityCompilationError(f"capability {field} must be a non-empty string")
    return value


def _validate_package(package: str, capability_id: str) -> None:
    path = PurePosixPath(package)
    if path.is_absolute() or ".." in path.parts or not package.startswith("capabilities/"):
        raise CapabilityCompilationError(
            f"invalid capability package for {capability_id}: {package}"
        )


def _repository_root(path: Path) -> Path:
    resolved = path.resolve()
    if resolved.parent.name == "governance":
        return resolved.parent.parent
    return resolved.parent


def _validate_package_implementation(
    repository_root: Path,
    descriptor: CapabilityDescriptor,
) -> None:
    init_path = (
        repository_root
        / "src"
        / "atlas_ros"
        / descriptor.package
        / "__init__.py"
    )
    if not init_path.is_file():
        raise CapabilityCompilationError(
            f"capability package is missing: {descriptor.capability_id} {init_path}"
        )
    try:
        tree = ast.parse(init_path.read_text(encoding="utf-8"), filename=str(init_path))
    except (OSError, SyntaxError) as error:
        raise CapabilityCompilationError(
            f"capability package is unreadable or invalid: {descriptor.capability_id}"
        ) from error
    declared_id: str | None = None
    for node in tree.body:
        if not isinstance(node, ast.Assign) or not isinstance(node.value, ast.Constant):
            continue
        if not isinstance(node.value.value, str):
            continue
        has_capability_target = any(
            isinstance(target, ast.Name) and target.id == "CAPABILITY_ID"
            for target in node.targets
        )
        if has_capability_target:
            declared_id = node.value.value
            break
    if declared_id != descriptor.capability_id:
        raise CapabilityCompilationError(
            "capability package ID disagrees with catalog: "
            f"{descriptor.capability_id} declared={declared_id!r}"
        )


def _string_tuple(value: Any, field: str, capability_id: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not all(
        isinstance(item, str) and item for item in value
    ):
        raise CapabilityCompilationError(
            f"capability {field} must be a list of strings: {capability_id}"
        )
    if len(set(value)) != len(value):
        raise CapabilityCompilationError(
            f"capability {field} contains duplicates: {capability_id}"
        )
    return tuple(value)


def _optional_bool(
    payload: Mapping[str, Any],
    field: str,
    capability_id: str,
    *,
    default: bool,
) -> bool:
    value = payload.get(field, default)
    if not isinstance(value, bool):
        raise CapabilityCompilationError(
            f"capability {field} must be boolean: {capability_id}"
        )
    return value


def _nullable_bool(
    payload: Mapping[str, Any],
    field: str,
    capability_id: str,
) -> bool | None:
    if field not in payload:
        return None
    value = payload[field]
    if not isinstance(value, bool):
        raise CapabilityCompilationError(
            f"capability {field} must be boolean: {capability_id}"
        )
    return value
