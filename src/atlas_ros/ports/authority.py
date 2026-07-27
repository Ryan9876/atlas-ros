"""Read-only port for the GitHub-first initialization authority."""

from __future__ import annotations

from pathlib import PurePosixPath
from typing import Protocol


class AuthorityReader(Protocol):
    """Reads immutable, repository-scoped authority resources without provider writes."""

    def read_text(self, path: PurePosixPath, *, ref: str) -> str:
        """Return the exact UTF-8 resource named by an immutable Git ref."""
