from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

from scripts.validate_v700_current_drive_authority import (
    CurrentDriveAuthorityError,
    canonical_sha256,
    validate_current_drive_authority,
)

ROOT = Path(__file__).resolve().parents[2]


def payload() -> dict[str, object]:
    value = json.loads(
        (ROOT / "release/v700-current-drive-authority-migration.json").read_text(
            encoding="utf-8"
        )
    )
    assert isinstance(value, dict)
    return value


def resign(value: dict[str, object]) -> None:
    value.pop("authority_migration_sha256", None)
    value["authority_migration_sha256"] = canonical_sha256(value)


def test_current_drive_authority_is_promotion_ready() -> None:
    result = validate_current_drive_authority(payload())

    assert result["status"] == "current_drive_authority_migration_ready"
    assert result["current_drive_dependency_count"] == 1
    assert result["promotion_scope_complete"] is True
    assert result["pre_v6_history_required_for_promotion"] is False
    assert result["provider_writes"] == 0


def test_current_drive_authority_rejects_pre_v6_promotion_dependency() -> None:
    value = deepcopy(payload())
    value["pre_v6_history_required_for_promotion"] = True
    resign(value)

    with pytest.raises(CurrentDriveAuthorityError, match="pre-v6"):
        validate_current_drive_authority(value)


def test_current_drive_authority_rejects_digest_drift() -> None:
    value = deepcopy(payload())
    source = value["source_bootstrap"]
    assert isinstance(source, dict)
    source["github_target"] = "release/RELEASE_INDEX.md"

    with pytest.raises(CurrentDriveAuthorityError, match="target|digest"):
        validate_current_drive_authority(value)
