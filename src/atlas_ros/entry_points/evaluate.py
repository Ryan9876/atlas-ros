"""Evaluation-only command entry point."""

from __future__ import annotations

from atlas_ros.entry_points._legacy import forward_legacy


def main() -> None:
    """Load intelligence evaluation modules only for atlas-evaluate."""
    forward_legacy(("intelligence",))


if __name__ == "__main__":
    main()
