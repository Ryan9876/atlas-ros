from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .authority_migration import DriveRetention, ImplementationRegistry, TargetAuthority


class RecursiveInventoryItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    url: str = Field(min_length=1)
    item_type: Literal["file", "folder"]
    mime_type: str = ""
    parent_id: str = ""
    relative_path: str = Field(min_length=1)
    target_authority: TargetAuthority
    drive_retention: DriveRetention
    target_path: str = ""
    source_sha256: str = ""
    representation_sha256: str = ""
    representation_url: str = ""
    deletion_authorized: bool = False

    @model_validator(mode="after")
    def validate_representation(self) -> RecursiveInventoryItem:
        if self.deletion_authorized:
            raise ValueError("authority cutover cannot authorize Drive deletion")
        if self.target_authority == TargetAuthority.GITHUB:
            if not self.target_path or not self.source_sha256 or not self.representation_sha256:
                raise ValueError(f"{self.id} lacks checksum-bound GitHub representation")
            if self.source_sha256 != self.representation_sha256:
                raise ValueError(f"{self.id} representation checksum mismatch")
            if not self.representation_url.startswith("https://github.com/"):
                raise ValueError(f"{self.id} lacks GitHub representation URL")
        return self


class RecursiveDriveInventory(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[1] = 1
    generated_at: str
    source_folder_id: str = Field(min_length=1)
    bootstrap_file_id: str = Field(min_length=1)
    items: list[RecursiveInventoryItem]
    summary: dict[str, int]

    @model_validator(mode="after")
    def validate_inventory(self) -> RecursiveDriveInventory:
        ids = [item.id for item in self.items]
        if len(ids) != len(set(ids)):
            raise ValueError("recursive inventory contains duplicate item ids")
        known = set(ids) | {self.source_folder_id}
        missing_parents = sorted(
            item.parent_id for item in self.items if item.parent_id and item.parent_id not in known
        )
        if missing_parents:
            raise ValueError(f"recursive inventory has missing parents: {missing_parents}")
        expected = dict(Counter(item.drive_retention.value for item in self.items))
        if self.summary != expected:
            raise ValueError("recursive inventory summary does not match retention classes")
        bootstrap = [item for item in self.items if item.id == self.bootstrap_file_id]
        if len(bootstrap) != 1 or bootstrap[0].drive_retention != DriveRetention.BOOTSTRAP:
            raise ValueError("fixed Drive bootstrap must appear exactly once")
        unresolved = [
            item.id
            for item in self.items
            if item.drive_retention == DriveRetention.REVIEW_REQUIRED
        ]
        if unresolved:
            raise ValueError(f"recursive inventory contains unresolved items: {unresolved}")
        return self


class DriveAllowlist(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[1] = 1
    bootstrap_file_id: str = Field(min_length=1)
    allowed_retention: tuple[DriveRetention, ...] = (
        DriveRetention.BOOTSTRAP,
        DriveRetention.LEGACY_READ_ONLY,
        DriveRetention.HUMAN_SHARE_EXPORT,
        DriveRetention.GITHUB_UNSUITABLE,
    )

    def violations(self, inventory: RecursiveDriveInventory) -> tuple[str, ...]:
        allowed = set(self.allowed_retention)
        return tuple(
            sorted(item.id for item in inventory.items if item.drive_retention not in allowed)
        )


class DevelopmentRecordSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    record_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    disposition: str = Field(min_length=1)
    implemented_scope: str = ""
    remaining_scope: str = ""
    evidence: tuple[str, ...] = ()

    @property
    def digest(self) -> str:
        payload = self.model_dump(mode="json")
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha256(encoded).hexdigest()


class DevelopmentRecordReconciliation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[1] = 1
    generated_at: str
    source_head: str = Field(min_length=1)
    matched: tuple[str, ...]
    github_only: tuple[str, ...]
    notion_only: tuple[str, ...]
    drifted: tuple[str, ...]
    record_digests: dict[str, str]
    report_sha256: str

    @property
    def valid(self) -> bool:
        return not (self.github_only or self.notion_only or self.drifted)


def registry_snapshots(registry: ImplementationRegistry) -> list[DevelopmentRecordSnapshot]:
    return [
        DevelopmentRecordSnapshot(
            record_id=record.record_id,
            title=record.title,
            disposition=record.disposition.value,
            implemented_scope=record.implemented_scope,
            remaining_scope=record.remaining_scope,
            evidence=tuple(record.evidence),
        )
        for record in registry.records
    ]


def reconcile_development_records(
    github_records: list[DevelopmentRecordSnapshot],
    notion_records: list[DevelopmentRecordSnapshot],
    *,
    source_head: str,
) -> DevelopmentRecordReconciliation:
    github = {record.record_id: record for record in github_records}
    notion = {record.record_id: record for record in notion_records}
    shared = sorted(github.keys() & notion.keys())
    drifted = tuple(
        record_id
        for record_id in shared
        if github[record_id].digest != notion[record_id].digest
    )
    matched = tuple(record_id for record_id in shared if record_id not in drifted)
    record_digests = {record_id: github[record_id].digest for record_id in sorted(github)}
    canonical = {
        "source_head": source_head,
        "matched": matched,
        "github_only": tuple(sorted(github.keys() - notion.keys())),
        "notion_only": tuple(sorted(notion.keys() - github.keys())),
        "drifted": drifted,
        "record_digests": record_digests,
    }
    report_sha256 = hashlib.sha256(
        json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return DevelopmentRecordReconciliation(
        generated_at=datetime.now(UTC).isoformat(),
        report_sha256=report_sha256,
        **canonical,
    )


def load_recursive_inventory(path: Path) -> RecursiveDriveInventory:
    return RecursiveDriveInventory.model_validate_json(path.read_text(encoding="utf-8"))


def load_record_snapshots(path: Path) -> list[DevelopmentRecordSnapshot]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    records = payload["records"] if isinstance(payload, dict) else payload
    return [DevelopmentRecordSnapshot.model_validate(record) for record in records]


def write_reconciliation(report: DevelopmentRecordReconciliation, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(report.model_dump_json(indent=2) + "\n", encoding="utf-8")
