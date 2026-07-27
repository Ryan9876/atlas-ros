"""Fail-closed compiler for canonical YAML policy sources."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any, cast

import yaml

from atlas_ros.kernel.digests import sha256_digest
from atlas_ros.policy.registry import CompiledPolicy, PolicyRegistry


class PolicyCompilationError(ValueError):
    """Raised when canonical policy sources are ambiguous or invalid."""


def compile_policy_registry(paths: Iterable[Path]) -> PolicyRegistry:
    """Compile an ordered set of unique policy sources into an immutable registry."""
    compiled: dict[str, CompiledPolicy] = {}
    source_payload: list[dict[str, Any]] = []
    for path in sorted(paths, key=lambda candidate: candidate.as_posix()):
        policy, payload = _compile_one(path)
        if policy.policy_id in compiled:
            raise PolicyCompilationError(f"duplicate policy ID: {policy.policy_id}")
        compiled[policy.policy_id] = policy
        source_payload.append(payload)
    if not compiled:
        raise PolicyCompilationError("at least one policy source is required")
    return PolicyRegistry.create(compiled, sha256_digest(source_payload))


def _compile_one(path: Path) -> tuple[CompiledPolicy, dict[str, Any]]:
    try:
        loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    except OSError as error:
        raise PolicyCompilationError(f"cannot read policy source: {path}") from error
    except yaml.YAMLError as error:
        raise PolicyCompilationError(f"invalid YAML policy source: {path}") from error
    if not isinstance(loaded, Mapping):
        raise PolicyCompilationError(f"policy source must be a mapping: {path}")
    payload = cast(dict[str, Any], dict(loaded))
    allowed = {"schema_version", "policy_id", "lifecycle", "rules"}
    if set(payload) != allowed:
        raise PolicyCompilationError(f"policy source has unsupported or missing fields: {path}")
    schema_version = _required_string(payload, "schema_version", path)
    if schema_version != "1.0":
        raise PolicyCompilationError(f"unsupported policy schema version: {schema_version}")
    policy_id = _required_string(payload, "policy_id", path)
    lifecycle = _required_string(payload, "lifecycle", path)
    if lifecycle != "active":
        raise PolicyCompilationError(f"current registry cannot load non-active policy: {policy_id}")
    raw_rules = payload["rules"]
    if not isinstance(raw_rules, list) or not raw_rules or not all(isinstance(rule, str) and rule for rule in raw_rules):
        raise PolicyCompilationError(f"policy rules must be a non-empty list of strings: {path}")
    rules = tuple(cast(list[str], raw_rules))
    if len(set(rules)) != len(rules):
        raise PolicyCompilationError(f"policy contains duplicate rules: {policy_id}")
    canonical = {"schema_version": schema_version, "policy_id": policy_id, "lifecycle": lifecycle, "rules": list(rules)}
    return CompiledPolicy(policy_id, schema_version, lifecycle, rules, sha256_digest(canonical)), canonical


def _required_string(payload: Mapping[str, Any], field: str, path: Path) -> str:
    value = payload.get(field)
    if not isinstance(value, str) or not value:
        raise PolicyCompilationError(f"policy {field} must be a non-empty string: {path}")
    return value
