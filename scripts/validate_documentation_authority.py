"""Validate current Atlas ROS documentation authority and legacy-reference boundaries."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

CURRENT_FILES = (
    "README.md",
    "docs/CURRENT_DOCUMENTATION.md",
    "docs/runbooks/V620_PRODUCTION_OPERATOR_AND_RECOVERY.md",
    "release/RELEASE_MANIFEST.md",
    "release/RELEASE_SCOPE_V620.md",
    "release/RELEASE_NOTES_V620.md",
)

REQUIRED_AUTHORITY_FILES = (
    "README.md",
    "docs/CURRENT_DOCUMENTATION.md",
    "docs/runbooks/V620_PRODUCTION_OPERATOR_AND_RECOVERY.md",
)

LEGACY_PATTERN = re.compile(r"\bW(?:0?1|0?2|0?3A?|0?4)\b", re.IGNORECASE)
ACTIVE_PATTERN = re.compile(r"Atlas ROS v6\.2\.0", re.IGNORECASE)
ROLLBACK_PATTERN = re.compile(r"Atlas ROS v6\.1\.1", re.IGNORECASE)


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
            errors.append(f"missing v6.2.0 active-authority declaration: {relative}")
        if not ROLLBACK_PATTERN.search(text):
            errors.append(f"missing v6.1.1 rollback declaration: {relative}")

    migration = ROOT / "docs/migration/W_WORKFLOW_ARCHIVAL_MAPPING.md"
    if migration.is_file():
        text = migration.read_text(encoding="utf-8")
        if "HISTORICAL — NOT CURRENT AUTHORITY" not in text:
            errors.append("W-workflow archival mapping is not marked Historical")

    if errors:
        print("Documentation authority validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print("Documentation authority validation passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
