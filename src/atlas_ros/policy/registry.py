"""Typed immutable policy registry contracts."""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping


@dataclass(frozen=True)
class CompiledPolicy:
    """One validated canonical policy source."""

    policy_id: str
    schema_version: str
    lifecycle: str
    rules: tuple[str, ...]
    digest: str


@dataclass(frozen=True)
class PolicyRegistry:
    """Single process-wide snapshot; policies are keyed by canonical ID."""

    policies: Mapping[str, CompiledPolicy]
    digest: str

    @classmethod
    def create(cls, policies: Mapping[str, CompiledPolicy], digest: str) -> "PolicyRegistry":
        return cls(policies=MappingProxyType(dict(policies)), digest=digest)

    def require(self, policy_id: str) -> CompiledPolicy:
        try:
            return self.policies[policy_id]
        except KeyError as error:
            raise KeyError(f"required policy is unavailable: {policy_id}") from error
