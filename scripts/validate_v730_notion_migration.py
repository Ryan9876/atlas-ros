#!/usr/bin/env python3
"""Validate the unapplied additive v7.3.0 Notion migration against a schema fixture."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import yaml


class MigrationValidationError(ValueError):
    """Raised when the migration is unsafe, incompatible, or live-authorized."""


def _digest(value: object) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def validate_migration(migration_path: Path, fixture_path: Path) -> dict[str, Any]:
    migration = yaml.safe_load(migration_path.read_text(encoding="utf-8"))
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    if not isinstance(migration, dict) or not isinstance(fixture, dict):
        raise MigrationValidationError("migration and fixture must be objects")
    if migration.get("status") != "candidate_unapplied":
        raise MigrationValidationError("migration must remain candidate_unapplied")
    if migration.get("production_apply_authorized") is not False:
        raise MigrationValidationError("production migration must not be authorized")
    target = migration.get("target", {})
    if target.get("system") != "notion":
        raise MigrationValidationError("target system must be notion")
    if target.get("database") != fixture.get("database"):
        raise MigrationValidationError("database fixture does not match migration target")
    if target.get("data_source") != fixture.get("data_source"):
        raise MigrationValidationError("data source fixture does not match migration target")
    fields = set(fixture.get("fields", []))
    preconditions = migration.get("preconditions", {})
    required_existing = set(preconditions.get("required_existing_fields", []))
    required_absent = set(preconditions.get("required_absent_fields", []))
    missing = sorted(required_existing - fields)
    unexpectedly_present = sorted(required_absent & fields)
    if missing:
        raise MigrationValidationError(f"fixture is missing required fields: {missing}")
    if unexpectedly_present:
        raise MigrationValidationError(
            f"fixture already contains fields required to be absent: {unexpectedly_present}"
        )
    additive = migration.get("additive_fields", [])
    names = [item.get("name") for item in additive]
    if not additive or any(not name for name in names):
        raise MigrationValidationError("migration must declare named additive fields")
    if len(names) != len(set(names)):
        raise MigrationValidationError("additive fields must be unique")
    if set(names) != required_absent:
        raise MigrationValidationError("additive fields must match required-absent preconditions")
    if migration.get("destructive_operations") != []:
        raise MigrationValidationError("destructive operations are prohibited")
    forbidden = ("DROP ", "RENAME ", "TRASH", "DELETE", "REMOVE ")
    serialized = json.dumps(migration, sort_keys=True).upper()
    if any(token in serialized for token in forbidden):
        raise MigrationValidationError("migration contains a destructive operation token")
    projected_fields = sorted(fields | set(names))
    receipt = {
        "schema_version": "1.0",
        "migration_id": migration.get("migration_id"),
        "status": "validated_unapplied",
        "target_data_source": target.get("data_source"),
        "preconditions_passed": True,
        "additive_fields": sorted(names),
        "projected_field_count": len(projected_fields),
        "destructive_operations": 0,
        "live_reads": 0,
        "live_writes": 0,
        "production_apply_authorized": False,
        "migration_digest": _digest(migration),
        "fixture_digest": _digest(fixture),
        "projected_schema_digest": _digest(projected_fields),
    }
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--migration",
        type=Path,
        default=Path("release/v730-notion-schema-migration.yaml"),
    )
    parser.add_argument(
        "--fixture",
        type=Path,
        default=Path("release/v730-notion-schema-fixture.json"),
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    receipt = validate_migration(args.migration, args.fixture)
    rendered = json.dumps(receipt, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")


if __name__ == "__main__":
    main()
