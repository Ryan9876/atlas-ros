"""Immutable runtime representation of the canonical capability catalog."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType


@dataclass(frozen=True, slots=True)
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
    explicit_intent_required: bool
    authorization_required: bool
    digest: str

    @property
    def module_name(self) -> str:
        """Return the future responsibility-owned Python module for this capability."""
        return "atlas_ros." + self.package.replace("/", ".")


@dataclass(frozen=True, slots=True)
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
        values = dict(capabilities)
        if not values:
            raise ValueError("capability registry cannot be empty")
        if any(key != descriptor.capability_id for key, descriptor in values.items()):
            raise ValueError("capability registry keys must match descriptor IDs")
        packages = tuple(descriptor.package for descriptor in values.values())
        if len(set(packages)) != len(packages):
            raise ValueError("capability packages must be unique")
        provider_writers = sorted(
            descriptor.capability_id
            for descriptor in values.values()
            if descriptor.writes_providers
        )
        if provider_writers:
            raise ValueError(
                "capabilities cannot write providers: " + ", ".join(provider_writers)
            )
        planners = tuple(
            descriptor
            for descriptor in values.values()
            if descriptor.sole_planning_authority
        )
        if tuple(item.capability_id for item in planners) != (
            "atlas.execution-planning",
        ):
            raise ValueError(
                "capability registry requires atlas.execution-planning as sole planner"
            )
        if planners[0].advisory_only:
            raise ValueError("the sole planning authority cannot be advisory-only")
        reconciliation = values.get("atlas.reconciliation")
        if reconciliation is None:
            raise ValueError("atlas.reconciliation is required")
        if reconciliation.may_create_execution_intent is not False:
            raise ValueError("reconciliation cannot create execution intent")
        command_lifecycle = values.get("atlas.command-lifecycle")
        if command_lifecycle is not None and not (
            command_lifecycle.explicit_intent_required
            and command_lifecycle.authorization_required
        ):
            raise ValueError(
                "command lifecycle requires explicit intent and attended authorization"
            )
        return cls(
            capabilities=MappingProxyType(values),
            digest=digest,
            planning_authority_id=planners[0].capability_id,
        )

    @property
    def planning_authority(self) -> CapabilityDescriptor:
        """Return the only capability allowed to produce execution plans."""
        return self.capabilities[self.planning_authority_id]

    def require(self, capability_id: str) -> CapabilityDescriptor:
        """Return one required capability or fail closed on an unknown ID."""
        try:
            return self.capabilities[capability_id]
        except KeyError as error:
            raise KeyError(f"unknown capability: {capability_id}") from error
