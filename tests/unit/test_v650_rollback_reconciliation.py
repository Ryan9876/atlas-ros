from __future__ import annotations

import json
from pathlib import Path

import pytest

import tools.release.rollback_reconciliation as rollback_reconciliation


RECONCILIATION = Path("release/V650_IMMUTABLE_SOURCE_RECONCILIATION.json")


def test_checked_in_v650_reconciliation_is_valid() -> None:
    record = rollback_reconciliation.load_v650_reconciliation(RECONCILIATION)

    assert record.production_version == "6.5.0"
    assert record.immutable_source_manifest_declared_version == "6.2.0"
    assert record.canonical_active_manifest_declared_version == "6.5.0"
    assert record.immutable_history_rewrite_authorized is False
    assert record.provider_writes == 0


def test_v650_reconciliation_rejects_history_rewrite(tmp_path: Path) -> None:
    payload = json.loads(RECONCILIATION.read_text(encoding="utf-8"))
    payload["immutable_history_rewrite_authorized"] = True
    path = tmp_path / "reconciliation.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(
        rollback_reconciliation.RollbackReconciliationError,
        match="history_rewrite",
    ):
        rollback_reconciliation.load_v650_reconciliation(path)


def test_v650_reconciliation_rejects_unverified_hash(tmp_path: Path) -> None:
    payload = json.loads(RECONCILIATION.read_text(encoding="utf-8"))
    payload["published_final_wheel_sha256"] = "not-a-digest"
    path = tmp_path / "reconciliation.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(
        rollback_reconciliation.RollbackReconciliationError,
        match="wheel_sha256",
    ):
        rollback_reconciliation.load_v650_reconciliation(path)
