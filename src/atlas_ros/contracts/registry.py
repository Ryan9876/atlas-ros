"""Immutable runtime representation of the canonical contract catalog."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType


@dataclass(frozen=True, slots=True)
class ContractDescriptor:
    """One versioned canonical contract and its compatibility boundary."""

    contract_id: str
    schema_version: str
    owner: str
    schema_path: str
    readers: tuple[str, ...]
    writer: str
    migrations: tuple[str, ...]
    compatibility: str
    digest: str


@dataclass(frozen=True, slots=True)
class LegacyContractBoundary:
    """Locations where historical contract types may and may not be used."""

    allowed_only_in: tuple[str, ...]
    forbidden_from: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ContractRegistry:
    """Digest-bound immutable contract descriptors keyed by canonical ID."""

    contracts: Mapping[str, ContractDescriptor]
    lifecycle: LegacyContractBoundary
    digest: str

    @classmethod
    def create(
        cls,
        contracts: Mapping[str, ContractDescriptor],
        lifecycle: LegacyContractBoundary,
        digest: str,
    ) -> ContractRegistry:
        values = dict(contracts)
        if not values:
            raise ValueError("contract registry cannot be empty")
        if any(key != descriptor.contract_id for key, descriptor in values.items()):
            raise ValueError("contract registry keys must match descriptor IDs")
        schema_paths = tuple(descriptor.schema_path for descriptor in values.values())
        if len(set(schema_paths)) != len(schema_paths):
            raise ValueError("contract schema paths must be unique")
        return cls(
            contracts=MappingProxyType(values),
            lifecycle=lifecycle,
            digest=digest,
        )

    def require(self, contract_id: str) -> ContractDescriptor:
        """Return one required contract or fail closed on an unknown ID."""
        try:
            return self.contracts[contract_id]
        except KeyError as error:
            raise KeyError(f"unknown contract: {contract_id}") from error
