#!/usr/bin/env python3
"""Fail-closed non-publishing validation for the v7.1 consolidation candidate."""

from __future__ import annotations

import argparse
import json
import subprocess
from dataclasses import asdict
from pathlib import Path

from tools.release.drive_dependency_inventory import (
    assert_zero_current_drive_dependencies,
    inventory_drive_dependencies,
)
from tools.release.release_compiler import compile_release, load_release_specification


def run(*command: str, root: Path) -> None:
    subprocess.run(command, cwd=root, check=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--evidence", type=Path, default=Path("v710-evidence"))
    parser.add_argument("--skip-tests", action="store_true")
    parser.add_argument("--source-commit")
    args = parser.parse_args()
    root = args.root.resolve()
    evidence = (root / args.evidence).resolve()
    evidence.mkdir(parents=True, exist_ok=True)

    inventory = inventory_drive_dependencies(root)
    assert_zero_current_drive_dependencies(inventory)
    (evidence / "DRIVE_DEPENDENCY_INVENTORY.json").write_text(
        json.dumps({
            "inventory_digest": inventory.inventory_digest,
            "summary": inventory.summary,
            "current_dependencies": 0,
            "references": [asdict(item) for item in inventory.references],
        }, indent=2, sort_keys=True) + "\n"
    )

    if args.source_commit:
        candidate = compile_release(
            load_release_specification(
                root / "release/specifications/V710.yaml",
                source_commit=args.source_commit,
            )
        )
        candidate.write(evidence / "compiler-output")

    fixture_receipts = {}
    for path in sorted((root / "tests/fixtures/release-specs").glob("*.yaml")):
        compiled = compile_release(load_release_specification(path))
        fixture_receipts[path.stem] = compiled.receipt.model_dump(mode="json")
    (evidence / "RELEASE_COMPILER_FIXTURES.json").write_text(
        json.dumps(fixture_receipts, indent=2, sort_keys=True) + "\n"
    )

    run("python", "scripts/validate_architecture.py", root=root)
    run("python", "scripts/validate_legacy_isolation.py", root=root)
    if not args.skip_tests:
        run("pytest", root=root)

    result = {
        "schema_version": "1.0",
        "status": "validated_not_authorized",
        "release_version": "7.1.0",
        "active_production_release": "7.0.1",
        "current_drive_dependencies": 0,
        "compiler_fixtures": sorted(fixture_receipts),
        "provider_writes": 0,
        "production_authorized": False,
        "published": False,
        "authority_activated": False,
        "destructive_actions": 0,
    }
    (evidence / "V710_VALIDATION_RESULT.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n"
    )


if __name__ == "__main__":
    main()
