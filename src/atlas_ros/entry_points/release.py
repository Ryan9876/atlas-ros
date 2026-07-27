"""Release-tooling-only command entry point."""

from __future__ import annotations

from atlas_ros.entry_points._legacy import forward_legacy


def main() -> None:
    """Load release inventory and verification tooling only for atlas-release."""
    forward_legacy(("release",))


if __name__ == "__main__":
    main()
