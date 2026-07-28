"""Read-only ports for GitHub-first and live dynamic initialization authorities."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import PurePosixPath
from typing import Any, Literal, Protocol

from atlas_ros.contracts.authority import (
    IntegrationInventorySnapshot,
    SystemStateSnapshot,
)


class AuthorityReader(Protocol):
    """Reads immutable, repository-scoped authority resources without provider writes."""

    def read_text(self, path: PurePosixPath, *, ref: str) -> str:
        """Return the exact UTF-8 resource named by an immutable Git ref."""


class DynamicAuthorityReader(Protocol):
    """Reads the current Notion authorities without performing provider writes."""

    def read_system_state(self, url: str) -> SystemStateSnapshot:
        """Return the current governed System State projection."""

    def read_integration_inventory(self, reference: str) -> IntegrationInventorySnapshot:
        """Return the governed inventory using a page URL or direct data-source reference."""


class ConnectorLivenessReader(Protocol):
    """Performs minimal read-only probes for required production integrations."""

    def read_connector_liveness(self, names: frozenset[str]) -> Mapping[str, bool]:
        """Return current read availability for every requested integration name."""


class ImmutableAuthoritySnapshot(Protocol):
    """Minimal snapshot surface returned by the optional warm-runtime cache."""

    kind: str
    payload: Any


class ImmutableAuthorityCache(Protocol):
    """Authenticated cache surface used only for immutable authority material."""

    def get(
        self,
        *,
        key: str,
        auth_token: str,
        expected_source_digest: str,
        now_epoch: float | None = None,
    ) -> ImmutableAuthoritySnapshot:
        """Return a fresh digest-bound immutable snapshot."""

    def put(
        self,
        *,
        key: str,
        kind: Literal["immutable_authority_snapshot"],
        payload: Any,
        source_digest: str,
        auth_token: str,
        verified_at_epoch: float | None = None,
    ) -> ImmutableAuthoritySnapshot:
        """Store non-authoritative immutable material for an eligible warm path."""
