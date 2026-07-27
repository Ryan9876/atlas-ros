"""Compile a checksum-bound Google Drive migration and retirement ledger."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path, PurePosixPath
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
    source_root_id: str
    traversal_complete: bool
    visited_folder_ids: tuple[str, ...]
    inaccessible_item_ids: tuple[str, ...]
    unconsumed_page_tokens: int
    inventory_complete: bool
    inventory_sha256: str
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
    source_root_id: str = "trusted-unit-inventory",
    traversal_complete: bool = True,
    visited_folder_ids: tuple[str, ...] | None = None,
    inaccessible_item_ids: tuple[str, ...] = (),
    unconsumed_page_tokens: int = 0,
) -> DriveMigrationLedger:
    """Validate inventory coverage and compile deterministic migration evidence."""
    if generated_for_release != "7.0.0rc1":
        raise DriveMigrationLedgerError("candidate ledger must target 7.0.0rc1")
    if not source_root_id.strip():
        raise DriveMigrationLedgerError("Drive inventory source root ID is required")
    visited = visited_folder_ids or (source_root_id,)
    _unique_nonempty(visited, "visited folder IDs")
    _unique_nonempty(inaccessible_item_ids, "inaccessible item IDs")
    if source_root_id not in visited:
        raise DriveMigrationLedgerError("Drive inventory did not visit its source root")
    if unconsumed_page_tokens < 0:
        raise DriveMigrationLedgerError("unconsumed page-token count cannot be negative")

    items = tuple(_item(record) for record in records)
    if not items:
        raise DriveMigrationLedgerError("Drive migration inventory cannot be empty")
    ids = tuple(item.drive_id for item in items)
    if len(set(ids)) != len(ids):
        raise DriveMigrationLedgerError("Drive migration inventory contains duplicate IDs")
    verified_targets = tuple(
        item.github_target
        for item in items
        if item.migration_status in {"verified", "staged"}
        and item.github_target is not None
    )
    if len(set(verified_targets)) != len(verified_targets):
        raise DriveMigrationLedgerError(
            "resolved Drive items cannot share one GitHub target"
        )

    inventory_complete = (
        traversal_complete
        and not inaccessible_item_ids
        and unconsumed_page_tokens == 0
    )
    inventory_payload = {
        "schema_version": "1.0",
        "generated_for_release": generated_for_release,
        "source_root_id": source_root_id,
        "traversal_complete": traversal_complete,
        "visited_folder_ids": list(visited),
        "inaccessible_item_ids": list(inaccessible_item_ids),
        "unconsumed_page_tokens": unconsumed_page_tokens,
        "records": [asdict(item) for item in items],
    }
    inventory_sha256 = sha256_digest(inventory_payload)

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
    complete = inventory_complete and unresolved == 0 and all(
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
        "source_root_id": source_root_id,
        "traversal_complete": traversal_complete,
        "visited_folder_ids": list(visited),
        "inaccessible_item_ids": list(inaccessible_item_ids),
        "unconsumed_page_tokens": unconsumed_page_tokens,
        "inventory_complete": inventory_complete,
        "inventory_sha256": inventory_sha256,
        "items": [asdict(item) for item in items],
        "unresolved_authoritative_items": unresolved,
        "staged_current_dependencies": staged_dependencies,
        "verified_github_representations": represented,
        "complete_for_promotion_readiness": complete,
        "ready_for_post_promotion_retirement": retirement_ready,
    }
    return DriveMigrationLedger(
        schema_version="1.0",
        generated_for_release=generated_for_release,
        source_root_id=source_root_id,
        traversal_complete=traversal_complete,
        visited_folder_ids=visited,
        inaccessible_item_ids=inaccessible_item_ids,
        unconsumed_page_tokens=unconsumed_page_tokens,
        inventory_complete=inventory_complete,
        inventory_sha256=inventory_sha256,
        items=items,
        unresolved_authoritative_items=unresolved,
        staged_current_dependencies=staged_dependencies,
        verified_github_representations=represented,
        complete_for_promotion_readiness=complete,
        ready_for_post_promotion_retirement=retirement_ready,
        ledger_sha256=sha256_digest(payload),
    )


def load_and_compile(path: Path) -> DriveMigrationLedger:
    """Load normalized inventory evidence and compile a fail-closed ledger."""
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise DriveMigrationLedgerError(
            f"invalid Drive migration inventory: {path}"
        ) from error
    if isinstance(payload, list):
        return compile_ledger(
            payload,
            source_root_id="legacy-unverified-inventory",
            traversal_complete=False,
            visited_folder_ids=("legacy-unverified-inventory",),
            unconsumed_page_tokens=1,
        )
    if not isinstance(payload, dict):
        raise DriveMigrationLedgerError(
            "Drive migration inventory must be a JSON object or legacy list"
        )
    records = payload.get("records")
    if not isinstance(records, list):
        raise DriveMigrationLedgerError("Drive migration inventory records must be a list")
    visited = _string_tuple(payload.get("visited_folder_ids"), "visited folder IDs")
    inaccessible = _string_tuple(
        payload.get("inaccessible_item_ids"),
        "inaccessible item IDs",
    )
    traversal_complete = payload.get("traversal_complete")
    if not isinstance(traversal_complete, bool):
        raise DriveMigrationLedgerError("Drive traversal_complete must be a boolean")
    unconsumed = payload.get("unconsumed_page_tokens")
    if not isinstance(unconsumed, int) or isinstance(unconsumed, bool):
        raise DriveMigrationLedgerError(
            "Drive unconsumed_page_tokens must be an integer"
        )
    return compile_ledger(
        records,
        generated_for_release=str(payload.get("generated_for_release", "")),
        source_root_id=str(payload.get("source_root_id", "")),
        traversal_complete=traversal_complete,
        visited_folder_ids=visited,
        inaccessible_item_ids=inaccessible,
        unconsumed_page_tokens=unconsumed,
    )


def load_ledger(path: Path) -> DriveMigrationLedger:
    """Read a compiled ledger and verify every derived field and its digest."""
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise DriveMigrationLedgerError(f"invalid Drive migration ledger: {path}") from error
    if not isinstance(payload, dict):
        raise DriveMigrationLedgerError("Drive migration ledger must be a JSON object")
    raw_items = payload.get("items")
    if not isinstance(raw_items, list):
        raise DriveMigrationLedgerError("Drive migration ledger items must be a list")
    compiled = compile_ledger(
        raw_items,
        generated_for_release=str(payload.get("generated_for_release", "")),
        source_root_id=str(payload.get("source_root_id", "")),
        traversal_complete=payload.get("traversal_complete") is True,
        visited_folder_ids=_string_tuple(
            payload.get("visited_folder_ids"),
            "visited folder IDs",
        ),
        inaccessible_item_ids=_string_tuple(
            payload.get("inaccessible_item_ids"),
            "inaccessible item IDs",
        ),
        unconsumed_page_tokens=_required_int(
            payload.get("unconsumed_page_tokens"),
            "unconsumed page tokens",
        ),
    )
    if payload != asdict(compiled):
        raise DriveMigrationLedgerError(
            "Drive migration ledger readback differs from compiled item evidence"
        )
    return compiled


def write_ledger(ledger: DriveMigrationLedger, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(asdict(ledger), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


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
        missing = (
            sorted(required - set(record))
            if isinstance(record, dict)
            else sorted(required)
        )
        raise DriveMigrationLedgerError(
            "Drive migration item missing fields: " + ", ".join(missing)
        )
    item = DriveMigrationItem(
        **{key: record.get(key) for key in DriveMigrationItem.__dataclass_fields__}
    )
    if not item.drive_id or not item.title or not item.mime_type or not item.modified_time:
        raise DriveMigrationLedgerError(
            "Drive migration item identity fields cannot be empty"
        )
    if item.size_bytes is not None and item.size_bytes < 0:
        raise DriveMigrationLedgerError(f"invalid Drive size for {item.drive_id}")
    _sha(item.drive_content_sha256, f"Drive content checksum for {item.drive_id}")
    if item.github_content_sha256 is not None:
        _sha(item.github_content_sha256, f"GitHub checksum for {item.drive_id}")
    if item.github_target is not None:
        _safe_target(item.github_target, item.drive_id)
    _validate_state(item)
    return item


def _validate_state(item: DriveMigrationItem) -> None:
    if item.migration_status in {"verified", "staged"}:
        if not item.github_target or not item.github_content_sha256 or not item.content_equivalent:
            raise DriveMigrationLedgerError(
                f"resolved Drive item lacks equivalent GitHub evidence: {item.drive_id}"
            )
        if item.drive_content_sha256 != item.github_content_sha256:
            raise DriveMigrationLedgerError(
                f"Drive and GitHub checksums differ: {item.drive_id}"
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
    invalid_historical_authority = (
        item.classification == "historical_authority"
        and (
            item.migration_status != "verified"
            or item.disposition != "retain_immutable_github"
        )
    )
    if invalid_historical_authority:
        raise DriveMigrationLedgerError(
            f"historical authority is not immutably represented: {item.drive_id}"
        )
    invalid_non_authoritative_disposition = (
        item.classification in {"duplicate", "obsolete"}
        and item.disposition
        not in {
            "eligible_for_retirement",
            "retain_legacy_read_only",
        }
    )
    if invalid_non_authoritative_disposition:
        raise DriveMigrationLedgerError(
            f"invalid non-authoritative disposition: {item.drive_id}"
        )


def _promotion_ready(item: DriveMigrationItem) -> bool:
    return (
        item.migration_status in {"verified", "staged"}
        and item.github_target is not None
        and item.github_content_sha256 is not None
        and item.content_equivalent
        and item.drive_content_sha256 == item.github_content_sha256
    )


def _safe_target(value: str, drive_id: str) -> None:
    target = PurePosixPath(value)
    if target.is_absolute() or ".." in target.parts:
        raise DriveMigrationLedgerError(
            f"unsafe GitHub target for {drive_id}: {value}"
        )


def _sha(value: str, field: str) -> None:
    if len(value) != 64 or any(
        character not in "0123456789abcdef" for character in value
    ):
        raise DriveMigrationLedgerError(f"{field} is not a lowercase SHA-256")


def _unique_nonempty(values: tuple[str, ...], field: str) -> None:
    if any(not value.strip() for value in values):
        raise DriveMigrationLedgerError(f"Drive {field} must contain non-empty IDs")
    if len(set(values)) != len(values):
        raise DriveMigrationLedgerError(f"Drive {field} contains duplicates")


def _string_tuple(value: Any, field: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise DriveMigrationLedgerError(f"Drive {field} must be a list of strings")
    return tuple(value)


def _required_int(value: Any, field: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise DriveMigrationLedgerError(f"Drive {field} must be an integer")
    return value


__all__ = [
    "DriveMigrationItem",
    "DriveMigrationLedger",
    "DriveMigrationLedgerError",
    "compile_ledger",
    "load_and_compile",
    "load_ledger",
    "write_ledger",
]
