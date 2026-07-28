"""Optional authenticated read-only warm-runtime cache foundation."""

from __future__ import annotations

import hmac
import json
import os
import time
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any, Literal

from atlas_ros.contracts.digests import canonical_json_bytes, sha256_digest

SnapshotKind = Literal[
    "compiled_policy",
    "validated_catalog",
    "schema",
    "capability_metadata",
    "immutable_authority_snapshot",
]

_ALLOWED_KINDS = frozenset(
    {
        "compiled_policy",
        "validated_catalog",
        "schema",
        "capability_metadata",
        "immutable_authority_snapshot",
    }
)


class WarmRuntimeError(ValueError):
    """Raised when warm-runtime state is unauthenticated, stale, or unsafe."""


@dataclass(frozen=True, slots=True)
class WarmRuntimeConfig:
    root: Path
    auth_token_sha256: str
    ttl_seconds: int = 300
    max_entries: int = 128

    def __post_init__(self) -> None:
        if len(self.auth_token_sha256) != 64 or any(
            character not in "0123456789abcdef" for character in self.auth_token_sha256
        ):
            raise WarmRuntimeError("warm-runtime authentication digest is invalid")
        if self.ttl_seconds <= 0:
            raise WarmRuntimeError("warm-runtime TTL must be positive")
        if self.max_entries <= 0:
            raise WarmRuntimeError("warm-runtime entry budget must be positive")


@dataclass(frozen=True, slots=True)
class WarmSnapshot:
    key: str
    kind: SnapshotKind
    payload: Any
    payload_digest: str
    source_digest: str
    verified_at_epoch: float
    expires_at_epoch: float


class WarmRuntimeCache:
    """Disposable local cache for verified read-only canonical snapshots."""

    def __init__(self, config: WarmRuntimeConfig) -> None:
        self._config = config
        self._root = config.root.resolve()
        self._root.mkdir(parents=True, exist_ok=True)
        os.chmod(self._root, 0o700)

    def put(
        self,
        *,
        key: str,
        kind: SnapshotKind,
        payload: Any,
        source_digest: str,
        auth_token: str,
        verified_at_epoch: float | None = None,
    ) -> WarmSnapshot:
        self._authenticate(auth_token)
        self._validate_key(key)
        if kind not in _ALLOWED_KINDS:
            raise WarmRuntimeError(f"unsupported warm-runtime snapshot kind: {kind}")
        self._require_digest(source_digest, "source")
        self._enforce_entry_budget(key)
        verified = time.time() if verified_at_epoch is None else verified_at_epoch
        snapshot = WarmSnapshot(
            key=key,
            kind=kind,
            payload=payload,
            payload_digest=sha256_digest(payload),
            source_digest=source_digest,
            verified_at_epoch=verified,
            expires_at_epoch=verified + self._config.ttl_seconds,
        )
        encoded = {
            "schema_version": "1.0",
            "key": snapshot.key,
            "kind": snapshot.kind,
            "payload": snapshot.payload,
            "payload_digest": snapshot.payload_digest,
            "source_digest": snapshot.source_digest,
            "verified_at_epoch": snapshot.verified_at_epoch,
            "expires_at_epoch": snapshot.expires_at_epoch,
            "provider_writes": 0,
            "authoritative": False,
        }
        path = self._path(key)
        temporary = path.with_suffix(".tmp")
        temporary.write_bytes(canonical_json_bytes(encoded))
        os.chmod(temporary, 0o600)
        temporary.replace(path)
        return snapshot

    def get(
        self,
        *,
        key: str,
        auth_token: str,
        expected_source_digest: str,
        now_epoch: float | None = None,
    ) -> WarmSnapshot:
        self._authenticate(auth_token)
        self._validate_key(key)
        self._require_digest(expected_source_digest, "expected source")
        path = self._path(key)
        if not path.is_file():
            raise WarmRuntimeError(f"warm-runtime snapshot is unavailable: {key}")
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise WarmRuntimeError("warm-runtime snapshot is unreadable") from error
        if not isinstance(raw, dict):
            raise WarmRuntimeError("warm-runtime snapshot must be an object")
        if raw.get("provider_writes") != 0 or raw.get("authoritative") is not False:
            raise WarmRuntimeError("warm-runtime snapshot violates non-authoritative boundary")
        kind = raw.get("kind")
        if kind not in _ALLOWED_KINDS:
            raise WarmRuntimeError("warm-runtime snapshot kind is invalid")
        payload = raw.get("payload")
        payload_digest = raw.get("payload_digest")
        source_digest = raw.get("source_digest")
        if not isinstance(payload_digest, str) or sha256_digest(payload) != payload_digest:
            raise WarmRuntimeError("warm-runtime payload digest does not match")
        if source_digest != expected_source_digest:
            raise WarmRuntimeError("warm-runtime source digest is stale or mismatched")
        expires = raw.get("expires_at_epoch")
        verified = raw.get("verified_at_epoch")
        if not isinstance(expires, int | float) or not isinstance(verified, int | float):
            raise WarmRuntimeError("warm-runtime freshness metadata is invalid")
        now = time.time() if now_epoch is None else now_epoch
        if now > float(expires):
            raise WarmRuntimeError("warm-runtime snapshot has expired")
        return WarmSnapshot(
            key=key,
            kind=kind,
            payload=payload,
            payload_digest=payload_digest,
            source_digest=source_digest,
            verified_at_epoch=float(verified),
            expires_at_epoch=float(expires),
        )

    def clear(self, *, auth_token: str) -> int:
        """Dispose of temporary cache state; this never touches provider records."""
        self._authenticate(auth_token)
        removed = 0
        for path in self._root.glob("*.json"):
            path.unlink()
            removed += 1
        return removed

    def _authenticate(self, token: str) -> None:
        actual = sha256(token.encode("utf-8")).hexdigest()
        if not hmac.compare_digest(actual, self._config.auth_token_sha256):
            raise WarmRuntimeError("warm-runtime authentication failed")

    def _path(self, key: str) -> Path:
        return self._root / (sha256(key.encode("utf-8")).hexdigest() + ".json")

    def _enforce_entry_budget(self, key: str) -> None:
        target = self._path(key)
        entries = tuple(self._root.glob("*.json"))
        if target not in entries and len(entries) >= self._config.max_entries:
            raise WarmRuntimeError("warm-runtime entry budget would be exceeded")

    @staticmethod
    def _validate_key(key: str) -> None:
        if not key or len(key) > 256 or "\x00" in key:
            raise WarmRuntimeError("warm-runtime key is invalid")

    @staticmethod
    def _require_digest(value: str, label: str) -> None:
        if len(value) != 64 or any(
            character not in "0123456789abcdef" for character in value
        ):
            raise WarmRuntimeError(f"{label} digest is invalid")
