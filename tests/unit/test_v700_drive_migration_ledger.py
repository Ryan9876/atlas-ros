from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

import pytest

from tools.release.drive_migration_ledger import (
    DriveMigrationLedgerError,
    compile_ledger,
    load_ledger,
    write_ledger,
)


def record(
    drive_id: str,
    *,
    target: str,
    digest: str,
    classification: str = "historical_authority",
    status: str = "verified",
    disposition: str = "retain_immutable_github",
) -> dict[str, object]:
    return {
        "drive_id": drive_id,
        "title": drive_id,
        "mime_type": "application/zip",
        "size_bytes": 2048,
        "modified_time": "2026-07-27T00:00:00Z",
        "owned_by_me": True,
        "shared": False,
        "drive_content_sha256": digest,
        "classification": classification,
        "github_target": target,
        "github_content_sha256": digest,
        "content_equivalent": True,
        "migration_status": status,
        "disposition": disposition,
    }


def ledger():
    return compile_ledger(
        [
            record(
                "release-v650",
                target="releases/v6.5.0/atlas-ros-6.5.0.tar.gz",
                digest="a" * 64,
            ),
            record(
                "release-v620",
                target="releases/v6.2.0/atlas-ros-6.2.0.tar.gz",
                digest="b" * 64,
            ),
        ]
    )


def test_ledger_is_deterministic_and_promotion_ready() -> None:
    first = ledger()
    replay = ledger()

    assert first.ledger_sha256 == replay.ledger_sha256
    assert first.unresolved_authoritative_items == 0
    assert first.verified_github_representations == 2
    assert first.complete_for_promotion_readiness is True
    assert first.ready_for_post_promotion_retirement is True


def test_ledger_rejects_checksum_mismatch() -> None:
    item = record(
        "release-v650",
        target="releases/v6.5.0/atlas-ros-6.5.0.tar.gz",
        digest="a" * 64,
    )
    item["github_content_sha256"] = "b" * 64

    with pytest.raises(DriveMigrationLedgerError, match="checksums differ"):
        compile_ledger([item])


def test_ledger_rejects_duplicate_verified_target() -> None:
    target = "releases/shared/source.tar.gz"

    with pytest.raises(DriveMigrationLedgerError, match="share one GitHub target"):
        compile_ledger(
            [
                record("one", target=target, digest="a" * 64),
                record("two", target=target, digest="b" * 64),
            ]
        )


def test_ledger_rejects_unsafe_target() -> None:
    with pytest.raises(DriveMigrationLedgerError, match="unsafe GitHub target"):
        compile_ledger(
            [
                record(
                    "release-v650",
                    target="../outside/source.tar.gz",
                    digest="a" * 64,
                )
            ]
        )


def test_compiled_ledger_readback_rejects_tampering(tmp_path: Path) -> None:
    path = tmp_path / "drive-ledger.json"
    write_ledger(ledger(), path)
    assert load_ledger(path) == ledger()

    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["verified_github_representations"] = 1
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(DriveMigrationLedgerError, match="readback differs"):
        load_ledger(path)


def test_ledger_write_contains_no_provider_action_authority(tmp_path: Path) -> None:
    path = tmp_path / "drive-ledger.json"
    compiled = ledger()
    write_ledger(compiled, path)
    payload = json.loads(path.read_text(encoding="utf-8"))

    assert payload == asdict(compiled)
    assert "deletion_authorized" not in path.read_text(encoding="utf-8")
    assert "provider_action" not in path.read_text(encoding="utf-8")
