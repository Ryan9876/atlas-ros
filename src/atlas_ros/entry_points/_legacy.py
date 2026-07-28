"""Lazy compatibility dispatch for commands not yet extracted from the legacy CLI."""

from __future__ import annotations

import sys
from collections.abc import Sequence


def forward_legacy(prefix: Sequence[str] = ()) -> None:
    """Import the legacy command implementation only after dispatch is resolved."""
    from atlas_ros.cli import main as legacy_main

    original = sys.argv
    try:
        sys.argv = [original[0], *prefix, *original[1:]]
        legacy_main()
    finally:
        sys.argv = original
