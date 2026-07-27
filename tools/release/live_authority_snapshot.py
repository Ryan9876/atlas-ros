"""Digest-bound live authority readback evidence for Atlas ROS v7 release control."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal

from atlas_ros.contracts.digests import sha256_digest

AuthorityName = Literal[
    "release_index",
    "system_state",
    "active_manifest",
    "integration_inventory",
]
SnapshotPhase = Literal["pre_promotion_baseline", "post_activation"]

_REQUIRED_AUTHORITIES = {
    "release_index",
    "system_state",
    "active_manifest",
    "integration_inventory",
}
_REQUIRED_INTEGRATIONS = {"GitHub", "Notion", "Todoist"}


class LiveAuthoritySnapshotError(ValueError):
    """Raised when live authority evidence is incomplete or contradictory."""


@dataclass(frozen=True, slots=True)
class AuthorityReadback:
    name: AuthorityName
    source_url: str
    observed_active_version: str
    observed_rollback_version: str
    content_sha256: str
    readback_passed: bool


@dataclass(frozen=True, slots=True)
class IntegrationReadback:
    name: str
    source_url: str
    connected: bool
    approved: bool
    accepted: bool
    current: bool
    least_privilege_verified: bool


@dataclass(frozen=True, slots=True)
class LiveAuthoritySnapshot:
    schema_version: Literal["1.0"]
    phase: SnapshotPhase
    exact_package_commit: str
    exact_artifact_digest: str
    staged_authority_digest: str
    expected_active_version: str
    expected_rollback_version: str
    authorities: tuple[AuthorityReadback, ...]
    required_integrations: tuple[IntegrationReadback, ...]
    complete: bool
    snapshot_sha256: str


def compile_snapshot(
    *,
    phase: SnapshotPhase,
    exact_package_commit: str,
    exact_artifact_digest: str,
    staged_authority_digest: str,
    expected_active_version: str,
    expected_rollback_version: str,
    authorities: list[dict[str, Any]],
    required_integrations: list[dict[str, Any]],
) -> LiveAuthoritySnapshot:
    """Compile one exact-package-bound live readback snapshot."""
    _sha(exact_package_commit, "exact package commit", 40)
    _sha(exact_artifact_digest, "exact artifact digest", 64)
    _sha(staged_authority_digest, "staged authority digest", 64)
    if phase == "pre_promotion_baseline":
        if expected_active_version != "6.5.0" or expected_rollback_version != "6.2.0":
            raise LiveAuthoritySnapshotError(
                "pre-promotion baseline must verify v6.5.0 with v6.2.0 rollback"
            )
    elif expected_active_version != "7.0.0" or expected_rollback_version != "6.5.0":
        raise LiveAuthoritySnapshotError(
            "post-activation readback must verify v7.0.0 with v6.5.0 rollback"
        )

    authority_records = tuple(_authority(item) for item in authorities)
    authority_names = {item.name for item in authority_records}
    if authority_names != _REQUIRED_AUTHORITIES:
        raise LiveAuthoritySnapshotError(
            "live snapshot must contain exactly the four required authorities"
        )
    if len(authority_records) != len(authority_names):
        raise LiveAuthoritySnapshotError("live snapshot contains duplicate authorities")

    integration_records = tuple(_integration(item) for item in required_integrations)
    integration_names = {item.name for item in integration_records}
    if integration_names != _REQUIRED_INTEGRATIONS:
        raise LiveAuthoritySnapshotError(
            "live snapshot must contain exactly GitHub, Notion, and Todoist"
        )
    if len(integration_records) != len(integration_names):
        raise LiveAuthoritySnapshotError(
            "live snapshot contains duplicate required integrations"
        )

    authorities_ready = all(
        item.readback_passed
        and item.observed_active_version == expected_active_version
        and item.observed_rollback_version == expected_rollback_version
        for item in authority_records
    )
    integrations_ready = all(
        item.connected
        and item.approved
        and item.accepted
        and item.current
        and item.least_privilege_verified
        for item in integration_records
    )
    complete = authorities_ready and integrations_ready
    payload = {
        "schema_version": "1.0",
        "phase": phase,
        "exact_package_commit": exact_package_commit,
        "exact_artifact_digest": exact_artifact_digest,
        "staged_authority_digest": staged_authority_digest,
        "expected_active_version": expected_active_version,
        "expected_rollback_version": expected_rollback_version,
        "authorities": [asdict(item) for item in authority_records],
        "required_integrations": [asdict(item) for item in integration_records],
        "complete": complete,
    }
    return LiveAuthoritySnapshot(
        schema_version="1.0",
        phase=phase,
        exact_package_commit=exact_package_commit,
        exact_artifact_digest=exact_artifact_digest,
        staged_authority_digest=staged_authority_digest,
        expected_active_version=expected_active_version,
        expected_rollback_version=expected_rollback_version,
        authorities=authority_records,
        required_integrations=integration_records,
        complete=complete,
        snapshot_sha256=sha256_digest(payload),
    )


def load_snapshot(path: Path) -> LiveAuthoritySnapshot:
    """Load a compiled snapshot and verify every derived field and digest."""
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise LiveAuthoritySnapshotError(f"invalid live authority snapshot: {path}") from error
    if not isinstance(payload, dict):
        raise LiveAuthoritySnapshotError("live authority snapshot must be a JSON object")
    authorities = payload.get("authorities")
    integrations = payload.get("required_integrations")
    if not isinstance(authorities, list) or not isinstance(integrations, list):
        raise LiveAuthoritySnapshotError(
            "live authority snapshot records must be JSON lists"
        )
    compiled = compile_snapshot(
        phase=_phase(payload.get("phase")),
        exact_package_commit=str(payload.get("exact_package_commit", "")),
        exact_artifact_digest=str(payload.get("exact_artifact_digest", "")),
        staged_authority_digest=str(payload.get("staged_authority_digest", "")),
        expected_active_version=str(payload.get("expected_active_version", "")),
        expected_rollback_version=str(payload.get("expected_rollback_version", "")),
        authorities=authorities,
        required_integrations=integrations,
    )
    if payload != _json_mapping(asdict(compiled)):
        raise LiveAuthoritySnapshotError(
            "live authority snapshot readback differs from compiled evidence"
        )
    return compiled


def write_snapshot(snapshot: LiveAuthoritySnapshot, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(_json_mapping(asdict(snapshot)), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _authority(value: dict[str, Any]) -> AuthorityReadback:
    try:
        record = AuthorityReadback(**value)
    except TypeError as error:
        raise LiveAuthoritySnapshotError("invalid authority readback fields") from error
    if record.name not in _REQUIRED_AUTHORITIES:
        raise LiveAuthoritySnapshotError(f"unknown authority readback: {record.name}")
    _url(record.source_url, f"authority source for {record.name}")
    _sha(record.content_sha256, f"authority checksum for {record.name}", 64)
    return record


def _integration(value: dict[str, Any]) -> IntegrationReadback:
    try:
        record = IntegrationReadback(**value)
    except TypeError as error:
        raise LiveAuthoritySnapshotError("invalid integration readback fields") from error
    if record.name not in _REQUIRED_INTEGRATIONS:
        raise LiveAuthoritySnapshotError(f"unknown required integration: {record.name}")
    _url(record.source_url, f"integration source for {record.name}")
    return record


def _phase(value: Any) -> SnapshotPhase:
    if value not in {"pre_promotion_baseline", "post_activation"}:
        raise LiveAuthoritySnapshotError("invalid live authority snapshot phase")
    return value


def _sha(value: str, field: str, length: int) -> None:
    if len(value) != length or any(
        character not in "0123456789abcdef" for character in value
    ):
        raise LiveAuthoritySnapshotError(
            f"{field} is not a lowercase {length}-character hexadecimal digest"
        )


def _url(value: str, field: str) -> None:
    if not value.startswith("https://"):
        raise LiveAuthoritySnapshotError(f"{field} must be an HTTPS URL")


def _json_mapping(value: dict[str, Any]) -> dict[str, Any]:
    normalized = json.loads(json.dumps(value, sort_keys=True))
    if not isinstance(normalized, dict):
        raise LiveAuthoritySnapshotError("live authority serialization must be an object")
    return normalized


__all__ = [
    "AuthorityReadback",
    "IntegrationReadback",
    "LiveAuthoritySnapshot",
    "LiveAuthoritySnapshotError",
    "compile_snapshot",
    "load_snapshot",
    "write_snapshot",
]
