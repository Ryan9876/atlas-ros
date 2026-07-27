"""Compile a checksum-bound Google Drive migration and retirement ledger."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal

from atlas_ros.contracts.digests import sha256_digest

Classification = Literal[
    "current_until_v7_activation",
    "historical_authority",
    "historical_evidence",
    "duplicate",
    "obsolete",
]
MigrationStatus = Literal["verified", "staged", "unresolved"]
Disposition = Literal[
    "retire_after_v7_activation",
    "retain_immutable_github",
    "retain_legacy_read_only",
    "eligible_for_retirement",
]


class DriveMigrationLedgerError(ValueError):
    """Raised when inventory evidence is incomplete, contradictory, or unsafe."""


@dataclass(frozen=True, slots=True)
class DriveMigrationItem:
    drive_id: str
    title: str
    mime_type: str
    size_bytes: int | None
    modified_time: str
    owned_by_me: bool
    shared: bool
    drive_content_sha256: str
    classification: Classification
    github_target: str | None
    github_content_sha256: str | None
    content_equivalent: bool
    migration_status: MigrationStatus
    disposition: Disposition
    notes: str = ""


@dataclass(frozen=True, slots=True)
class DriveMigrationLedger:
    schema_version: Literal["1.0"]
    generated_for_release: str
    items: tuple[DriveMigrationItem, ...]
    unresolved_authoritative_items: int
    staged_current_dependencies: int
    verified_github_representations: int
    complete_for_promotion_readiness: bool
    ready_for_post_promotion_retirement: bool
    ledger_sha256: str


def compile_ledger(
    records: list[dict[str, Any]],
    *,
    generated_for_release: str = "7.0.0rc1",
) -> DriveMigrationLedger:
    """Validate normalized Drive inventory and compile deterministic migration evidence."""
    if generated_for_release != "7.0.0rc1":
        raise DriveMigrationLedgerError("candidate ledger must target 7.0.0rc1")
    items = tuple(_item(record) for record in records)
    if not items:
        raise DriveMigrationLedgerError("Drive migration inventory cannot be empty")
    ids = tuple(item.drive_id for item in items)
    if len(set(ids)) != len(ids):
        raise DriveMigrationLedgerError("Drive migration inventory contains duplicate IDs")

    unresolved = sum(
        item.migration_status == "unresolved"
        and item.classification in {"current_until_v7_activation", "historical_authority"}
        for item in items
    )
    staged_dependencies = sum(
        item.classification == "current_until_v7_activation"
        and item.migration_status == "staged"
        for item in items
    )
    represented = sum(
        item.github_target is not None
        and item.github_content_sha256 is not None
        and item.content_equivalent
        for item in items
    )
    complete = unresolved == 0 and all(
        _promotion_ready(item)
        for item in items
        if item.classification in {
            "current_until_v7_activation",
            "historical_authority",
            "historical_evidence",
        }
    )
    retirement_ready = complete and staged_dependencies == 0 and all(
        item.classification != "current_until_v7_activation" for item in items
    )
    payload = {
        "schema_version": "1.0",
        "generated_for_release": generated_for_release,
        "items": [asdict(item) for item in items],
        "unresolved_authoritative_items": unresolved,
        "staged_current_dependencies": staged_dependencies,
        "verified_github_representations": represented,
        "complete_for_promotion_readiness": complete,
        "ready_for_post_promotion_retirement": retirement_ready,
    }
    return DriveMigrationLedger(
        **payload,
        ledger_sha256=sha256_digest(payload),
    )


def load_and_compile(path: Path) -> DriveMigrationLedger:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise DriveMigrationLedgerError(f"invalid Drive migration inventory: {path}") from error
    if not isinstance(payload, list):
        raise DriveMigrationLedgerError("Drive migration inventory must be a JSON list")
    return compile_ledger(payload)


def write_ledger(ledger: DriveMigrationLedger, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(ledger), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _item(record: dict[str, Any]) -> DriveMigrationItem:
    required = {
        "drive_id",
        "title",
        "mime_type",
        "size_bytes",
        "modified_time",
        "owned_by_me",
        "shared",
        "drive_content_sha256",
        "classification",
        "github_target",
        "github_content_sha256",
        "content_equivalent",
        "migration_status",
        "disposition",
    }
    if not isinstance(record, dict) or not required.issubset(record):
        missing = sorted(required - set(record)) if isinstance(record, dict) else sorted(required)
        raise DriveMigrationLedgerError("Drive migration item missing fields: " + ", ".join(missing))
    item = DriveMigrationItem(**{key: record.get(key) for key in DriveMigrationItem.__dataclass_fields__})
    if not item.drive_id or not item.title or not item.mime_type or not item.modified_time:
        raise DriveMigrationLedgerError("Drive migration item identity fields cannot be empty")
    if item.size_bytes is not None and item.size_bytes < 0:
        raise DriveMigrationLedgerError(f"invalid Drive size for {item.drive_id}")
    _sha(item.drive_content_sha256, f"Drive content checksum for {item.drive_id}")
    if item.github_content_sha256 is not None:
        _sha(item.github_content_sha256, f"GitHub checksum for {item.drive_id}")
    _validate_state(item)
    return item


def _validate_state(item: DriveMigrationItem) -> None:
    if item.migration_status in {"verified", "staged"}:
        if not item.github_target or not item.github_content_sha256 or not item.content_equivalent:
            raise DriveMigrationLedgerError(
                f"resolved Drive item lacks equivalent GitHub evidence: {item.drive_id}"
            )
    if item.classification == "current_until_v7_activation":
        if item.migration_status != "staged":
            raise DriveMigrationLedgerError(
                "current bootstrap must remain staged until v7 activation"
            )
        if item.disposition != "retire_after_v7_activation":
            raise DriveMigrationLedgerError(
                "current bootstrap must retire only after v7 activation"
            )
    if item.classification == "historical_authority":
        if item.migration_status != "verified" or item.disposition != "retain_immutable_github":
            raise DriveMigrationLedgerError(
                f"historical authority is not immutably represented: {item.drive_id}"
            )
    if item.classification in {"duplicate", "obsolete"} and item.disposition not in {
        "eligible_for_retirement",
        "retain_legacy_read_only",
    }:
        raise DriveMigrationLedgerError(
            f"invalid non-authoritative disposition: {item.drive_id}"
        )


def _promotion_ready(item: DriveMigrationItem) -> bool:
    return (
        item.migration_status in {"verified", "staged"}
        and item.github_target is not None
        and item.github_content_sha256 is not None
        and item.content_equivalent
    )


def _sha(value: str, field: str) -> None:
    if len(value) != 64 or any(character not in "0123456789abcdef" for character in value):
        raise DriveMigrationLedgerError(f"{field} is not a lowercase SHA-256")
