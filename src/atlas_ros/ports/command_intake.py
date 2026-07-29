"""Attended lifecycle-command intake boundary."""
from __future__ import annotations

from typing import Protocol

from atlas_ros.contracts.operational_awareness import CommandSourceRefV1


class CommandIntakePort(Protocol):
    """Return explicit commands from an attended, authorized source."""

    def read_command(self, source_id: str) -> CommandSourceRefV1: ...
