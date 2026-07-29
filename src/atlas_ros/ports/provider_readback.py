"""Readback requirements for awareness and lifecycle integrations."""
from __future__ import annotations

from typing import Any, Protocol


class ProviderStateReadbackPort(Protocol):
    """Read one provider object projection for independent verification."""

    def readback(self, *, provider: str, target: str) -> dict[str, Any]: ...
