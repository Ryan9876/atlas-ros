"""Validate current Atlas ROS documentation authority and historical-reference boundaries."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

CURRENT_FILES = (
    "README.md",
    "docs/CURRENT_DOCUMENTATION.md",
    "docs/runbooks/V650_PRODUCTION_OPERATOR_AND_RECOVERY.md",
    "release/RELEASE_MANIFEST.md",
    "release/RELEASE_NOTES_V650.md",
)

REQUIRED_AUTHORITY_FILES = (
    "README.md",
    "docs/CURRENT_DOCUMENTATION.md",
    "docs/runbooks/V650_PRODUCTION_OPERATOR_AND_RECOVERY.md",
)

SUPERSEDED_MUTABLE_GUIDANCE = (
    "docs/runbooks/V620_PRODUCTION_OPERATOR_AND_RECOVERY.md",
    "docs/migration/W_WORKFLOW_ARCHIVAL_MAPPING.md",
)

LEGACY_PATTERN = re.compile(r"\bW(?:0?1|0?2|0?3A?|0?4)\b", re.IGNORECASE)
ACTIVE_PATTERN = re.compile(r"Atlas ROS v6\.5\.0", re.IGNORECASE)
ROLLBACK_PATTERN = re.compile(r"Atlas ROS v6\.2\.0", re.IGNORECASE)
HISTORICAL_MARKER = "HISTORICAL — NOT CURRENT AUTHORITY"


def main() -> int:
    errors: list[str] = []

    for relative in CURRENT_FILES:
        path = ROOT / relative
        if not path.is_file():
            errors.append(f"missing current authority file: {relative}")
            continue

        text = path.read_text(encoding="utf-8")
        matches = sorted(set(LEGACY_PATTERN.findall(text)))
        if matches:
            errors.append(
                f"legacy numbered-workflow term(s) in current guidance {relative}: "
                + ", ".join(matches)
            )

    for relative in REQUIRED_AUTHORITY_FILES:
        path = ROOT / relative
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        if not ACTIVE_PATTERN.search(text):
            errors.append(f"missing v6.5.0 active-authority declaration: {relative}")
        if not ROLLBACK_PATTERN.search(text):
            errors.append(f"missing v6.2.0 rollback declaration: {relative}")

    for relative in SUPERSEDED_MUTABLE_GUIDANCE:
        path = ROOT / relative
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        if HISTORICAL_MARKER not in text:
            errors.append(f"superseded guidance is not marked Historical: {relative}")

    if errors:
        print("Documentation authority validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print("Documentation authority validation passed for Atlas ROS v6.5.0.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
