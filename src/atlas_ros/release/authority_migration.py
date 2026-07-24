from __future__ import annotations

import json
import re
from collections import Counter
from datetime import datetime, timezone
from enum import StrEnum
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

_RELEASE_TITLE = re.compile(
    r"^Atlas(?:[ _]ROS)?[ _]v?\d+\.\d+(?:\.\d+)?(?:[- _].*)?$",
    re.IGNORECASE,
)
_RELEASE_COMPANION = re.compile(r"Atlas.*restoration companion", re.IGNORECASE)
_GOOGLE_NATIVE_PREFIX = "application/vnd.google-apps."


class TargetAuthority(StrEnum):
    GITHUB = "github"
    DRIVE_BOOTSTRAP = "drive_bootstrap"
    NOTION_OR_RUNTIME = "notion_or_runtime"
    DRIVE_EXCEPTION = "drive_exception"
    REVIEW_REQUIRED = "review_required"


class DriveRetention(StrEnum):
    BOOTSTRAP = "bootstrap"
    LEGACY_READ_ONLY = "legacy_read_only"
    TEMPORARY_MIGRATION = "temporary_migration"
    HUMAN_SHARE_EXPORT = "human_share_export"
    GITHUB_UNSUITABLE = "github_unsuitable"
    REVIEW_REQUIRED = "review_required"


class DriveItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    url: str = Field(min_length=1)
    mime_type: str = ""
    item_type: Literal["file", "folder"]
    created_time: str = ""
    modified_time: str = ""
    parent_id: str = ""


class ClassifiedDriveItem(DriveItem):
    target_authority: TargetAuthority
    drive_retention: DriveRetention
    rationale: str = Field(min_length=1)
    target_path: str = ""
    checksum_required: bool = True
    deletion_authorized: bool = False


class DriveInventory(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[1] = 1
    generated_at: str
    source_folder_id: str = Field(min_length=1)
    items: list[ClassifiedDriveItem]
    summary: dict[str, int]

    @model_validator(mode="after")
    def validate_inventory(self) -> DriveInventory:
        identifiers = [item.id for item in self.items]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("drive inventory contains duplicate item ids")
        expected = dict(Counter(item.drive_retention.value for item in self.items))
        if self.summary != expected:
            raise ValueError("drive inventory summary does not match item classifications")
        if any(item.deletion_authorized for item in self.items):
            raise ValueError("inventory classification cannot authorize deletion")
        return self


class ImplementationDisposition(StrEnum):
    FULLY_IMPLEMENTED = "fully_implemented"
    PARTIALLY_IMPLEMENTED = "partially_implemented"
    IN_PROGRESS = "in_progress"
    DEFERRED = "deferred"
    SUPERSEDED = "superseded"
    DECLINED = "declined"
    UNAFFECTED = "unaffected"


class ImplementationRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    record_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    disposition: ImplementationDisposition
    implemented_scope: str = ""
    remaining_scope: str = ""
    evidence: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_disposition(self) -> ImplementationRecord:
        if self.disposition in {
            ImplementationDisposition.FULLY_IMPLEMENTED,
            ImplementationDisposition.PARTIALLY_IMPLEMENTED,
            ImplementationDisposition.IN_PROGRESS,
        } and not self.evidence:
            raise ValueError(f"{self.record_id} requires implementation evidence")
        if self.disposition == ImplementationDisposition.PARTIALLY_IMPLEMENTED:
            if not self.implemented_scope or not self.remaining_scope:
                raise ValueError(
                    f"{self.record_id} partial implementation requires "
                    "implemented and remaining scope"
                )
        if self.disposition == ImplementationDisposition.FULLY_IMPLEMENTED and self.remaining_scope:
            raise ValueError(f"{self.record_id} is fully implemented but has remaining scope")
        return self


class ImplementationRegistry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[1] = 1
    generated_at: str
    candidate_version: str = Field(min_length=1)
    source_head: str = Field(min_length=1)
    records: list[ImplementationRecord]

    @model_validator(mode="after")
    def validate_registry(self) -> ImplementationRegistry:
        identifiers = [record.record_id for record in self.records]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("implementation registry contains duplicate record ids")
        return self


def _slug(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return normalized or "untitled"


def classify_drive_item(item: DriveItem, *, bootstrap_file_id: str) -> ClassifiedDriveItem:
    title = item.title.strip()
    is_google_native = item.mime_type.startswith(_GOOGLE_NATIVE_PREFIX)

    if item.id == bootstrap_file_id:
        return ClassifiedDriveItem(
            **item.model_dump(),
            target_authority=TargetAuthority.DRIVE_BOOTSTRAP,
            drive_retention=DriveRetention.BOOTSTRAP,
            rationale=(
                "Fixed initialization pointer required until a later bootstrap decision "
                "supersedes it."
            ),
            target_path="authority/bootstrap/RELEASE_INDEX.md",
            checksum_required=True,
        )

    if title.casefold() == "release_index.md" and is_google_native:
        return ClassifiedDriveItem(
            **item.model_dump(),
            target_authority=TargetAuthority.GITHUB,
            drive_retention=DriveRetention.TEMPORARY_MIGRATION,
            rationale=(
                "Duplicate Google-native release index should migrate to GitHub and retire "
                "after readback."
            ),
            target_path="authority/legacy/duplicate-release-index.md",
            checksum_required=True,
        )

    if _RELEASE_TITLE.match(title) or _RELEASE_COMPANION.search(title):
        return ClassifiedDriveItem(
            **item.model_dump(),
            target_authority=TargetAuthority.GITHUB,
            drive_retention=DriveRetention.LEGACY_READ_ONLY,
            rationale=(
                "Immutable software release history belongs in GitHub Releases; the Drive "
                "copy remains read-only during migration."
            ),
            target_path=f"releases/legacy/{_slug(title)}",
            checksum_required=True,
        )

    if title.casefold() == "development":
        return ClassifiedDriveItem(
            **item.model_dump(),
            target_authority=TargetAuthority.GITHUB,
            drive_retention=DriveRetention.TEMPORARY_MIGRATION,
            rationale="Version-controlled development artifacts belong in GitHub.",
            target_path="migration/legacy-development",
            checksum_required=True,
        )

    if title.casefold() == "archive":
        return ClassifiedDriveItem(
            **item.model_dump(),
            target_authority=TargetAuthority.GITHUB,
            drive_retention=DriveRetention.LEGACY_READ_ONLY,
            rationale=(
                "Historical software authority should be checksum-migrated to GitHub and "
                "preserved read-only during transition."
            ),
            target_path="releases/legacy/archive",
            checksum_required=True,
        )

    if title.casefold() == "runtime":
        return ClassifiedDriveItem(
            **item.model_dump(),
            target_authority=TargetAuthority.NOTION_OR_RUNTIME,
            drive_retention=DriveRetention.REVIEW_REQUIRED,
            rationale=(
                "Mutable runtime state does not belong in GitHub and should move to Notion "
                "or the governed runtime store."
            ),
            checksum_required=False,
        )

    if is_google_native:
        return ClassifiedDriveItem(
            **item.model_dump(),
            target_authority=TargetAuthority.REVIEW_REQUIRED,
            drive_retention=DriveRetention.REVIEW_REQUIRED,
            rationale=(
                "Google-native content requires an explicit decision between GitHub source "
                "and a human-sharing exception."
            ),
            checksum_required=True,
        )

    return ClassifiedDriveItem(
        **item.model_dump(),
        target_authority=TargetAuthority.GITHUB,
        drive_retention=DriveRetention.TEMPORARY_MIGRATION,
        rationale=(
            "Default version-controlled artifact classification is GitHub migration with "
            "Drive retained only during verification."
        ),
        target_path=f"migration/unclassified/{_slug(title)}",
        checksum_required=True,
    )


def build_drive_inventory(
    items: list[DriveItem], *, source_folder_id: str, bootstrap_file_id: str
) -> DriveInventory:
    classified = [
        classify_drive_item(item, bootstrap_file_id=bootstrap_file_id) for item in items
    ]
    summary = dict(Counter(item.drive_retention.value for item in classified))
    return DriveInventory(
        generated_at=datetime.now(timezone.utc).isoformat(),
        source_folder_id=source_folder_id,
        items=classified,
        summary=summary,
    )


def load_drive_items(path: Path) -> list[DriveItem]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    raw_items = payload["items"] if isinstance(payload, dict) else payload
    return [DriveItem.model_validate(item) for item in raw_items]


def write_drive_inventory(inventory: DriveInventory, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(inventory.model_dump_json(indent=2) + "\n", encoding="utf-8")


def load_drive_inventory(path: Path) -> DriveInventory:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return DriveInventory.model_validate(payload)


def load_implementation_registry(path: Path) -> ImplementationRegistry:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return ImplementationRegistry.model_validate(payload)
