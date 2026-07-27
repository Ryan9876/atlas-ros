"""Read-only ports for GitHub-first and live dynamic initialization authorities."""

from __future__ import annotations

from pathlib import PurePosixPath
from typing import Protocol

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

    def read_integration_inventory(self, url: str) -> IntegrationInventorySnapshot:
        """Return the current governed Integration Inventory projection."""
