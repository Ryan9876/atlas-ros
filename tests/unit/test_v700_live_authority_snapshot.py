from __future__ import annotations

import json
from dataclasses import asdict, replace
from pathlib import Path

import pytest

from tools.release.live_authority_snapshot import (
    LiveAuthoritySnapshotError,
    compile_snapshot,
    load_snapshot,
    write_snapshot,
)


def authorities(
    *,
    active: str = "6.5.0",
    rollback: str = "6.2.0",
    passed: bool = True,
) -> list[dict[str, object]]:
    return [
        {
            "name": name,
            "source_url": f"https://authority.example/{name}",
            "observed_active_version": active,
            "observed_rollback_version": rollback,
            "content_sha256": digest * 64,
            "readback_passed": passed,
        }
        for name, digest in (
            ("release_index", "a"),
            ("system_state", "b"),
            ("active_manifest", "c"),
            ("integration_inventory", "d"),
        )
    ]


def integrations(*, current: bool = True) -> list[dict[str, object]]:
    return [
        {
            "name": name,
            "source_url": f"https://integration.example/{name.lower()}",
            "connected": True,
            "approved": True,
            "accepted": True,
            "current": current,
            "least_privilege_verified": True,
        }
        for name in ("GitHub", "Notion", "Todoist")
    ]


def snapshot():
    return compile_snapshot(
        phase="pre_promotion_baseline",
        exact_package_commit="e" * 40,
        exact_artifact_digest="f" * 64,
        staged_authority_digest="1" * 64,
        expected_active_version="6.5.0",
        expected_rollback_version="6.2.0",
        authorities=authorities(),
        required_integrations=integrations(),
    )


def test_live_authority_snapshot_is_exact_package_bound_and_complete() -> None:
    compiled = snapshot()
    replay = snapshot()

    assert compiled.complete is True
    assert compiled.exact_package_commit == "e" * 40
    assert compiled.exact_artifact_digest == "f" * 64
    assert compiled.snapshot_sha256 == replay.snapshot_sha256


def test_live_authority_snapshot_records_version_or_integration_mismatch() -> None:
    version_mismatch = compile_snapshot(
        phase="pre_promotion_baseline",
        exact_package_commit="e" * 40,
        exact_artifact_digest="f" * 64,
        staged_authority_digest="1" * 64,
        expected_active_version="6.5.0",
        expected_rollback_version="6.2.0",
        authorities=authorities(active="6.2.0"),
        required_integrations=integrations(),
    )
    integration_mismatch = compile_snapshot(
        phase="pre_promotion_baseline",
        exact_package_commit="e" * 40,
        exact_artifact_digest="f" * 64,
        staged_authority_digest="1" * 64,
        expected_active_version="6.5.0",
        expected_rollback_version="6.2.0",
        authorities=authorities(),
        required_integrations=integrations(current=False),
    )

    assert version_mismatch.complete is False
    assert integration_mismatch.complete is False


def test_live_authority_snapshot_requires_exact_source_sets() -> None:
    with pytest.raises(LiveAuthoritySnapshotError, match="four required authorities"):
        compile_snapshot(
            phase="pre_promotion_baseline",
            exact_package_commit="e" * 40,
            exact_artifact_digest="f" * 64,
            staged_authority_digest="1" * 64,
            expected_active_version="6.5.0",
            expected_rollback_version="6.2.0",
            authorities=authorities()[:-1],
            required_integrations=integrations(),
        )


def test_live_authority_snapshot_readback_rejects_tampering(tmp_path: Path) -> None:
    path = tmp_path / "live-authority.json"
    write_snapshot(snapshot(), path)
    assert load_snapshot(path) == snapshot()

    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["complete"] = False
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(LiveAuthoritySnapshotError, match="readback differs"):
        load_snapshot(path)


def test_post_activation_snapshot_requires_v7_identity() -> None:
    with pytest.raises(LiveAuthoritySnapshotError, match="post-activation"):
        compile_snapshot(
            phase="post_activation",
            exact_package_commit="e" * 40,
            exact_artifact_digest="f" * 64,
            staged_authority_digest="1" * 64,
            expected_active_version="6.5.0",
            expected_rollback_version="6.2.0",
            authorities=authorities(),
            required_integrations=integrations(),
        )


def test_snapshot_json_contains_no_authority_to_write(tmp_path: Path) -> None:
    path = tmp_path / "live-authority.json"
    compiled = snapshot()
    write_snapshot(compiled, path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    normalized = json.loads(json.dumps(asdict(compiled), sort_keys=True))

    assert payload == normalized
    assert "write" not in path.read_text(encoding="utf-8").lower()
    assert replace(compiled, complete=False).snapshot_sha256 == compiled.snapshot_sha256
