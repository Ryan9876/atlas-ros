"""Migration-tooling-only command entry point."""

from __future__ import annotations

import sys

from atlas_ros.entry_points._legacy import forward_legacy

_ALLOWED = {
    "classify-drive-inventory",
    "validate-drive-inventory",
    "validate-implementation-registry",
}


def main() -> None:
    """Expose only migration commands from the legacy release surface."""
    if len(sys.argv) < 2 or sys.argv[1] not in _ALLOWED:
        allowed = ", ".join(sorted(_ALLOWED))
        raise SystemExit(f"atlas-migrate requires one of: {allowed}")
    forward_legacy(("release",))


if __name__ == "__main__":
    main()
