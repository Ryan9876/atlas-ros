from __future__ import annotations

import json
from dataclasses import asdict, replace
from pathlib import Path

import pytest

from tools.release.rollback_evidence import (
    RollbackEvidenceError,
    RollbackPackageEvidence,
    load_receipt,
    reconcile_v650_rollback,
    write_receipt,
)


def evidence() -> RollbackPackageEvidence:
    return RollbackPackageEvidence(
        target_version="6.5.0",
        target_tag="v6.5.0",
        source_commit="a" * 40,
        source_commit_message="release: add explicit v6.5.0 publication controller",
        package_version="6.5.0",
        manifest_declared_version="6.2.0",
        manifest_sha256="b" * 64,
        release_asset_version="6.5.0",
        release_tag_points_to_source=True,
        published_release_readable=True,
        publication_checksums_passed=True,
        source_archive_sha256="c" * 64,
        wheel_sha256="d" * 64,
        clean_install_version="6.5.0",
        clean_install_passed=True,
        restoration_tests_passed=True,
        metadata_exception_record_url="https://app.notion.com/rollback-exception",
        metadata_exception_acknowledges_manifest_mismatch=True,
        provider_writes_during_validation=0,
    )


def test_v650_rollback_evidence_reconciles_stale_immutable_manifest() -> None:
    receipt = reconcile_v650_rollback(evidence())

    assert receipt.status == "ready"
    assert receipt.verified_version == "6.5.0"
    assert receipt.metadata_discrepancy is True
    assert receipt.metadata_exception_record_url
    assert receipt.provider_writes == 0
    assert receipt.immutable_history_rewritten is False
    assert receipt.restoration_performed is False
    assert receipt.authority_changed is False


def test_manifest_mismatch_requires_governed_exception_record() -> None:
    receipt = reconcile_v650_rollback(
        replace(
            evidence(),
            metadata_exception_record_url=None,
            metadata_exception_acknowledges_manifest_mismatch=False,
        )
    )

    assert receipt.status == "blocked"
    assert (
        "stale immutable manifest requires a governed metadata-exception record"
        in receipt.blockers
    )
    assert (
        "metadata-exception record must acknowledge the manifest-version mismatch"
        in receipt.blockers
    )


def test_actual_release_or_restoration_identity_cannot_be_overridden_by_exception() -> None:
    receipt = reconcile_v650_rollback(
        replace(
            evidence(),
            package_version="6.2.0",
            clean_install_passed=False,
            restoration_tests_passed=False,
        )
    )

    assert receipt.status == "blocked"
    assert "package metadata does not identify v6.5.0" in receipt.blockers
    assert "clean installation has not passed" in receipt.blockers
    assert "rollback restoration tests has not passed" in receipt.blockers


def test_rollback_evidence_rejects_provider_writes() -> None:
    receipt = reconcile_v650_rollback(
        replace(evidence(), provider_writes_during_validation=1)
    )

    assert receipt.status == "blocked"
    assert "rollback evidence validation performed provider writes" in receipt.blockers
    assert receipt.provider_writes == 0


def test_rollback_evidence_roundtrip_rejects_tampering(tmp_path: Path) -> None:
    path = tmp_path / "rollback-evidence.json"
    receipt = reconcile_v650_rollback(evidence())
    write_receipt(evidence(), receipt, path)
    assert load_receipt(path) == receipt

    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["receipt"]["status"] = "blocked"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(RollbackEvidenceError, match="readback differs"):
        load_receipt(path)


def test_written_receipt_contains_no_release_or_authority_action(tmp_path: Path) -> None:
    path = tmp_path / "rollback-evidence.json"
    receipt = reconcile_v650_rollback(evidence())
    write_receipt(evidence(), receipt, path)
    payload = json.loads(path.read_text(encoding="utf-8"))

    assert payload["evidence"] == json.loads(
        json.dumps(asdict(evidence()), sort_keys=True)
    )
    assert payload["receipt"]["immutable_history_rewritten"] is False
    assert payload["receipt"]["restoration_performed"] is False
    assert payload["receipt"]["authority_changed"] is False
