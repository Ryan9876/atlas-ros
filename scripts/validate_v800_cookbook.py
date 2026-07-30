#!/usr/bin/env python3
"""Verify that v8.0.0 cookbook examples match shared conformance fixtures."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def validate(cookbook: Path, fixtures: Path) -> dict[str, object]:
    text = cookbook.read_text(encoding="utf-8")
    cases = json.loads(fixtures.read_text(encoding="utf-8"))
    required_boundaries = (
        "Interpretation does not authorize execution.",
        "Planning does not authorize execution.",
        "Adapters cannot create execution intent.",
        "Provider writes require the existing attended and governed authorization path.",
        "Natural-language inference does not expand permissions or execution scope.",
        "One-active-checkpoint rule",
        "Idempotency and replay",
        "Reconciliation",
    )
    missing = [item for item in required_boundaries if item not in text]
    example_texts = [
        item["text"]
        for group in ("positive_delegation", "negative_delegation")
        for item in cases[group]
    ]
    missing.extend(item for item in example_texts[:6] if item not in text)
    if missing:
        raise ValueError(f"cookbook is missing governed content: {missing}")
    return {
        "status": "passed",
        "version": "8.0.0",
        "positive_fixture_count": len(cases["positive_delegation"]),
        "negative_fixture_count": len(cases["negative_delegation"]),
        "provider_writes": 0,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--cookbook", type=Path,
        default=Path("docs/operations/ATLAS_ROS_V800_DELEGATION_COOKBOOK.md"),
    )
    parser.add_argument(
        "--fixtures", type=Path,
        default=Path("tests/fixtures/operational-awareness/v800-task-update-delegation.json"),
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    receipt = validate(args.cookbook, args.fixtures)
    rendered = json.dumps(receipt, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")


if __name__ == "__main__":
    main()
