"""Validate that compatibility paths are isolated from canonical runtime commands."""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

from atlas_ros.validation.architecture_v7 import PACKAGE_ROOT, imported_modules


class LegacyIsolationError(ValueError):
    """Raised when a legacy or migration path remains production-reachable."""


def validate(root: Path, registry_path: Path) -> list[str]:
    errors: list[str] = []
    main = root / "entry_points" / "main.py"
    forbidden = {
        "atlas_ros.cli",
        "atlas_ros.entry_points._legacy",
        "atlas_ros.contracts.migrations",
        "atlas_ros.release",
    }
    for module in sorted(imported_modules(main)):
        if any(module == item or module.startswith(item + ".") for item in forbidden):
            errors.append(f"canonical dispatcher imports compatibility path: {module}")

    loaded = yaml.safe_load(registry_path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict) or loaded.get("schema_version") != "1.0":
        errors.append("compatibility registry schema is invalid")
        return errors
    entries = loaded.get("compatibility_paths")
    if not isinstance(entries, list) or not entries:
        errors.append("compatibility registry is empty")
        return errors
    for entry in entries:
        if not isinstance(entry, dict):
            errors.append("compatibility registry entry must be a mapping")
            continue
        required = {"id", "path", "owner", "review_condition", "tests", "production_reachable"}
        if not required.issubset(entry):
            errors.append(f"compatibility entry is incomplete: {entry.get('id', '<unknown>')}")
            continue
        if entry["production_reachable"] is not False:
            errors.append(f"compatibility path is production-reachable: {entry['id']}")
        path = Path(str(entry["path"]))
        if not (registry_path.parent.parent / path).exists():
            errors.append(f"compatibility path is missing: {entry['path']}")
        tests = entry["tests"]
        if not isinstance(tests, list) or not tests:
            errors.append(f"compatibility path has no tests: {entry['id']}")
    return errors


def main() -> None:
    errors = validate(PACKAGE_ROOT, Path("governance/compatibility-paths.yaml"))
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        raise SystemExit(1)
    print("legacy and compatibility isolation passed")


if __name__ == "__main__":
    main()
