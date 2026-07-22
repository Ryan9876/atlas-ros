from __future__ import annotations

from collections.abc import Callable
from copy import deepcopy
from typing import Any

Migration = Callable[[dict[str, Any]], dict[str, Any]]


class UnsupportedSchemaVersionError(ValueError):
    pass


class RecordMigrator:
    """Explicit, deterministic schema migration registry."""

    def __init__(self) -> None:
        self._migrations: dict[tuple[str, str], Migration] = {}

    def register(self, source: str, target: str, migration: Migration) -> None:
        key = (source, target)
        if key in self._migrations:
            raise ValueError(f"migration already registered: {source} -> {target}")
        self._migrations[key] = migration

    def migrate(self, payload: dict[str, Any], target: str) -> dict[str, Any]:
        current = str(payload.get("schema_version", ""))
        if current == target:
            return deepcopy(payload)
        migration = self._migrations.get((current, target))
        if migration is None:
            raise UnsupportedSchemaVersionError(f"no migration path: {current} -> {target}")
        migrated = migration(deepcopy(payload))
        migrated["schema_version"] = target
        migrated.pop("integrity_hash", None)
        return migrated
