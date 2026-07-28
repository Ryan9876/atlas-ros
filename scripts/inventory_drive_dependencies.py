#!/usr/bin/env python3
"""Write the deterministic Google Drive dependency inventory."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from tools.release.drive_dependency_inventory import (
    assert_zero_current_drive_dependencies,
    inventory_drive_dependencies,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--require-zero-current", action="store_true")
    args = parser.parse_args()
    inventory = inventory_drive_dependencies(args.root)
    if args.require_zero_current:
        assert_zero_current_drive_dependencies(inventory)
    payload = {
        "schema_version": "1.0",
        "root": inventory.root,
        "inventory_digest": inventory.inventory_digest,
        "summary": inventory.summary,
        "current_dependency_count": len(inventory.current_dependencies),
        "references": [asdict(item) for item in inventory.references],
        "provider_reads": 0,
        "provider_writes": 0,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
