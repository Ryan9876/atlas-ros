#!/usr/bin/env python3
"""Run a non-destructive exact Google Drive retirement simulation."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from tools.release.drive_retirement import (
    DriveRetirementAuthorization,
    DriveRetirementPreflight,
    simulate_retirement_transaction,
)


def _load(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise SystemExit(f"JSON input must be an object: {path}")
    return value


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--preflight", type=Path, required=True)
    parser.add_argument("--authorization", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    preflight_values = _load(args.preflight)
    authorization_values = _load(args.authorization)
    preflight_values["target_ids"] = tuple(preflight_values.get("target_ids", ()))
    authorization_values["exact_target_ids"] = tuple(
        authorization_values.get("exact_target_ids", ())
    )
    receipt = simulate_retirement_transaction(
        DriveRetirementPreflight(**preflight_values),
        DriveRetirementAuthorization(**authorization_values),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(asdict(receipt), indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
