"""Validate the immutable Atlas ROS v6.5.0 source reconciliation record."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class RollbackReconciliationError(ValueError):
    """Raised when rollback reconciliation evidence is incomplete or contradictory."""


@dataclass(frozen=True, slots=True)
class V650RollbackReconciliation:
    schema_version: str
    reconciliation_status: str
    production_version: str
    production_source_commit: str
    immutable_tag: str
    immutable_source_pyproject_version: str
    immutable_source_manifest_declared_version: str
    immutable_source_manifest_blob_sha: str
    canonical_active_manifest_declared_version: str
    canonical_active_manifest_blob_sha: str
    published_final_source_sha256: str
    published_final_wheel_sha256: str
    restoration_authority: str
    immediate_rollback_version: str
    immediate_rollback_commit: str
    immutable_history_rewrite_authorized: bool
    provider_writes: int
    notes: str


def load_v650_reconciliation(path: Path) -> V650RollbackReconciliation:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise RollbackReconciliationError(f"invalid reconciliation evidence: {path}") from error
    if not isinstance(payload, dict):
        raise RollbackReconciliationError("reconciliation evidence must be a JSON object")
    try:
        record = V650RollbackReconciliation(**payload)
    except TypeError as error:
        raise RollbackReconciliationError(
            "reconciliation evidence fields are incomplete"
        ) from error
    _validate(record)
    return record


def _validate(record: V650RollbackReconciliation) -> None:
    expected: dict[str, Any] = {
        "schema_version": "1.0",
        "reconciliation_status": "accepted_historical_metadata_defect",
        "production_version": "6.5.0",
        "production_source_commit": "bb6d6fea70d6824c9bc6a42e63ba36cc88029260",
        "immutable_tag": "v6.5.0",
        "immutable_source_pyproject_version": "6.5.0",
        "immutable_source_manifest_declared_version": "6.2.0",
        "canonical_active_manifest_declared_version": "6.5.0",
        "restoration_authority": "published_v6.5.0_release_assets_and_checksums",
        "immediate_rollback_version": "6.2.0",
        "immediate_rollback_commit": "863d5ddf9ebd4723200166cf31c7acd93ebec54f",
        "immutable_history_rewrite_authorized": False,
        "provider_writes": 0,
    }
    for field, value in expected.items():
        if getattr(record, field) != value:
            raise RollbackReconciliationError(
                f"unexpected v6.5 reconciliation value: {field}"
            )
    for field in (
        "immutable_source_manifest_blob_sha",
        "canonical_active_manifest_blob_sha",
        "published_final_source_sha256",
        "published_final_wheel_sha256",
    ):
        _lower_hex(getattr(record, field), field)
    if not record.notes.strip():
        raise RollbackReconciliationError("reconciliation notes cannot be empty")


def _lower_hex(value: str, field: str) -> None:
    expected_length = 40 if field.endswith("blob_sha") else 64
    if len(value) != expected_length or any(
        character not in "0123456789abcdef" for character in value
    ):
        raise RollbackReconciliationError(f"{field} is not valid lowercase hex")


__all__ = [
    "RollbackReconciliationError",
    "V650RollbackReconciliation",
    "load_v650_reconciliation",
]
