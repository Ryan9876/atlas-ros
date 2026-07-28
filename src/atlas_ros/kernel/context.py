"""Immutable context produced by successful Atlas ROS initialization."""

from __future__ import annotations

from dataclasses import dataclass

from atlas_ros.kernel.authority import AuthorityRecord


@dataclass(frozen=True)
class InitializationContext:
    """The authority-bound context every consequential runtime operation receives."""

    authority: AuthorityRecord
    release_index_markdown: str
    release_manifest_markdown: str
    system_state_url: str
    integration_inventory_url: str

    @property
    def active_commit(self) -> str:
        return self.authority.active_release.immutable_commit

    @property
    def active_version(self) -> str:
        return self.authority.active_release.version
