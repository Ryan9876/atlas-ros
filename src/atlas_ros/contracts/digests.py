"""Dependency-free deterministic digest primitives for canonical contracts."""

from __future__ import annotations

import hashlib
import json
from typing import Any


def canonical_json_bytes(value: Any) -> bytes:
    """Encode a value deterministically and reject unsupported objects."""
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
        default=_reject_unknown,
    ).encode("utf-8")


def sha256_digest(value: Any) -> str:
    """Return the SHA-256 digest of a canonical JSON representation."""
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def _reject_unknown(value: Any) -> object:
    raise TypeError(f"unsupported digest value: {type(value).__name__}")
