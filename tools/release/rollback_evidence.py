"""Reconcile immutable Atlas ROS v6.5 rollback evidence without rewriting history."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal

from atlas_ros.contracts.digests import sha256_digest

RollbackEvidenceStatus = Literal["ready", "blocked"]


class RollbackEvidenceError(ValueError):
    """Raised when rollback identity evidence is malformed or contradictory."""


@dataclass(frozen=True, slots=True)
class RollbackPackageEvidence:
    target_version: str
    target_tag: str
    source_commit: str
    source_commit_message: str
    package_version: str
    manifest_declared_version: str
    manifest_sha256: str
    release_asset_version: str
    release_tag_points_to_source: bool
    published_release_readable: bool
    publication_checksums_passed: bool
    source_archive_sha256: str
    wheel_sha256: str
    clean_install_version: str
    clean_install_passed: bool
    restoration_tests_passed: bool
    metadata_exception_record_url: str | None
    metadata_exception_acknowledges_manifest_mismatch: bool
    provider_writes_during_validation: int


@dataclass(frozen=True, slots=True)
class RollbackEvidenceReceipt:
    status: RollbackEvidenceStatus
    evidence_digest: str
    verified_version: Literal["6.5.0"]
    verified_tag: Literal["v6.5.0"]
    source_commit: str
    metadata_discrepancy: bool
    metadata_exception_record_url: str | None
    blockers: tuple[str, ...]
    verified_controls: tuple[str, ...]
    provider_writes: int
    immutable_history_rewritten: bool
    restoration_performed: bool
    authority_changed: bool


def reconcile_v650_rollback(evidence: RollbackPackageEvidence) -> RollbackEvidenceReceipt:
    """Reconcile v6.5 identity from immutable release and restoration evidence."""
    blockers: list[str] = []
    if evidence.target_version != "6.5.0" or evidence.target_tag != "v6.5.0":
        blockers.append("rollback identity must be Atlas ROS v6.5.0")
    _sha(evidence.source_commit, "rollback source commit", 40, blockers)
    _sha(evidence.manifest_sha256, "rollback manifest SHA-256", 64, blockers)
    _sha(evidence.source_archive_sha256, "rollback source SHA-256", 64, blockers)
    _sha(evidence.wheel_sha256, "rollback wheel SHA-256", 64, blockers)
    if not evidence.source_commit_message.strip():
        blockers.append("rollback source commit message is required")

    identities = {
        "package metadata": evidence.package_version,
        "release asset identity": evidence.release_asset_version,
        "clean installation": evidence.clean_install_version,
    }
    blockers.extend(
        f"{name} does not identify v6.5.0"
        for name, version in identities.items()
        if version != "6.5.0"
    )
    gates = {
        "release tag target": evidence.release_tag_points_to_source,
        "published release readability": evidence.published_release_readable,
        "publication checksums": evidence.publication_checksums_passed,
        "clean installation": evidence.clean_install_passed,
        "rollback restoration tests": evidence.restoration_tests_passed,
    }
    blockers.extend(f"{name} has not passed" for name, passed in gates.items() if not passed)

    discrepancy = evidence.manifest_declared_version != "6.5.0"
    if discrepancy:
        if not _valid_url(evidence.metadata_exception_record_url):
            blockers.append(
                "stale immutable manifest requires a governed metadata-exception record"
            )
        if not evidence.metadata_exception_acknowledges_manifest_mismatch:
            blockers.append(
                "metadata-exception record must acknowledge the manifest-version mismatch"
            )
    elif evidence.metadata_exception_acknowledges_manifest_mismatch:
        blockers.append(
            "metadata-exception acknowledgement is contradictory without a manifest mismatch"
        )

    if evidence.provider_writes_during_validation:
        blockers.append("rollback evidence validation performed provider writes")

    controls = (
        "verify immutable v6.5.0 tag target",
        "verify source and wheel checksums from the published release",
        "verify package metadata and clean installation report v6.5.0",
        "verify restoration tests from immutable GitHub assets",
        "preserve the stale immutable manifest as historical evidence",
        "bind the discrepancy to a governed metadata-exception record",
    )
    return RollbackEvidenceReceipt(
        status="blocked" if blockers else "ready",
        evidence_digest=sha256_digest(asdict(evidence)),
        verified_version="6.5.0",
        verified_tag="v6.5.0",
        source_commit=evidence.source_commit,
        metadata_discrepancy=discrepancy,
        metadata_exception_record_url=evidence.metadata_exception_record_url,
        blockers=tuple(blockers),
        verified_controls=controls,
        provider_writes=0,
        immutable_history_rewritten=False,
        restoration_performed=False,
        authority_changed=False,
    )


def load_receipt(path: Path) -> RollbackEvidenceReceipt:
    """Read a receipt and verify its digest by recompiling the embedded evidence."""
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise RollbackEvidenceError(f"invalid rollback evidence receipt: {path}") from error
    if not isinstance(payload, dict):
        raise RollbackEvidenceError("rollback evidence receipt must be a JSON object")
    raw_evidence = payload.get("evidence")
    raw_receipt = payload.get("receipt")
    if not isinstance(raw_evidence, dict) or not isinstance(raw_receipt, dict):
        raise RollbackEvidenceError(
            "rollback evidence file must contain evidence and receipt objects"
        )
    try:
        evidence = RollbackPackageEvidence(**raw_evidence)
    except TypeError as error:
        raise RollbackEvidenceError("invalid rollback package evidence fields") from error
    compiled = reconcile_v650_rollback(evidence)
    if raw_receipt != _json_mapping(asdict(compiled)):
        raise RollbackEvidenceError(
            "rollback evidence receipt readback differs from compiled evidence"
        )
    return compiled


def write_receipt(
    evidence: RollbackPackageEvidence,
    receipt: RollbackEvidenceReceipt,
    path: Path,
) -> None:
    """Write evidence and its deterministic receipt for independent readback."""
    expected = reconcile_v650_rollback(evidence)
    if receipt != expected:
        raise RollbackEvidenceError("rollback receipt does not match supplied evidence")
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": "1.0",
        "evidence": _json_mapping(asdict(evidence)),
        "receipt": _json_mapping(asdict(receipt)),
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _sha(value: str, field: str, length: int, blockers: list[str]) -> None:
    if len(value) != length or any(
        character not in "0123456789abcdef" for character in value
    ):
        blockers.append(
            f"{field} is not a lowercase {length}-character hexadecimal digest"
        )


def _valid_url(value: str | None) -> bool:
    return bool(value and value.startswith("https://") and len(value) > 8)


def _json_mapping(value: dict[str, object]) -> dict[str, object]:
    normalized = json.loads(json.dumps(value, sort_keys=True))
    if not isinstance(normalized, dict):
        raise RollbackEvidenceError("rollback evidence serialization must be an object")
    return normalized


__all__ = [
    "RollbackEvidenceError",
    "RollbackEvidenceReceipt",
    "RollbackPackageEvidence",
    "load_receipt",
    "reconcile_v650_rollback",
    "write_receipt",
]
