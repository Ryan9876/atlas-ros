"""Immutable runtime representation of the canonical capability catalog."""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping


@dataclass(frozen=True)
class CapabilityDescriptor:
    """One provider-neutral capability declared by the canonical catalog."""

    capability_id: str
    package: str
    owner: str
    writes_providers: bool
    inputs: tuple[str, ...]
    outputs: tuple[str, ...]
    sole_planning_authority: bool
    advisory_only: bool
    may_create_execution_intent: bool | None
    digest: str


@dataclass(frozen=True)
class CapabilityRegistry:
    """Digest-bound immutable capability descriptors keyed by canonical ID."""

    capabilities: Mapping[str, CapabilityDescriptor]
    digest: str
    planning_authority_id: str

    @classmethod
    def create(
        cls,
        capabilities: Mapping[str, CapabilityDescriptor],
        digest: str,
    ) -> CapabilityRegistry:
        planners = tuple(
            descriptor.capability_id
            for descriptor in capabilities.values()
            if descriptor.sole_planning_authority
        )
        if planners != ("atlas.execution-planning",):
            raise ValueError(
                "capability registry requires atlas.execution-planning as sole planner"
            )
        return cls(
            capabilities=MappingProxyType(dict(capabilities)),
            digest=digest,
            planning_authority_id=planners[0],
        )

    def require(self, capability_id: str) -> CapabilityDescriptor:
        """Return one required capability or fail closed on an unknown ID."""
        try:
            return self.capabilities[capability_id]
        except KeyError as error:
            raise KeyError(f"unknown capability: {capability_id}") from error
