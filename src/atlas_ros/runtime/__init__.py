"""Runtime primitives loaded only when their capability is selected."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .database import RuntimeDatabase
    from .outbox import Outbox

__all__ = ["Outbox", "RuntimeDatabase"]


def __getattr__(name: str) -> Any:
    if name == "RuntimeDatabase":
        from .database import RuntimeDatabase

        return RuntimeDatabase
    if name == "Outbox":
        from .outbox import Outbox

        return Outbox
    raise AttributeError(name)
