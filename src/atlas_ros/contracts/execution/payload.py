"""Checksum-bound provider payloads resolved separately from execution plans."""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from atlas_ros.contracts.digests import canonical_json_bytes, sha256_digest


class ProviderOperationPayload(BaseModel):
    """Exact JSON payload bound to one planned provider operation by digest."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    contract_id: Literal["atlas.provider-operation-payload"] = (
        "atlas.provider-operation-payload"
    )
    schema_version: Literal["1.0"] = "1.0"
    operation_id: str = Field(min_length=1, max_length=128)
    payload_json: str = Field(min_length=2, max_length=100_000)
    payload_digest: str = Field(pattern=r"^[0-9a-f]{64}$")

    @classmethod
    def create(
        cls,
        *,
        operation_id: str,
        payload: Mapping[str, Any],
    ) -> ProviderOperationPayload:
        normalized = dict(payload)
        encoded = canonical_json_bytes(normalized).decode("utf-8")
        return cls(
            operation_id=operation_id,
            payload_json=encoded,
            payload_digest=sha256_digest(normalized),
        )

    @property
    def data(self) -> dict[str, Any]:
        """Return a fresh decoded mapping for an exact adapter invocation."""
        loaded = json.loads(self.payload_json)
        if not isinstance(loaded, dict):
            raise ValueError("provider operation payload must decode to a mapping")
        return loaded

    @model_validator(mode="after")
    def validate_payload(self) -> ProviderOperationPayload:
        try:
            loaded = json.loads(self.payload_json)
        except json.JSONDecodeError as error:
            raise ValueError("provider operation payload is not valid JSON") from error
        if not isinstance(loaded, dict):
            raise ValueError("provider operation payload must be a JSON object")
        if canonical_json_bytes(loaded).decode("utf-8") != self.payload_json:
            raise ValueError("provider operation payload JSON is not canonical")
        if sha256_digest(loaded) != self.payload_digest:
            raise ValueError("provider operation payload digest does not match content")
        return self


__all__ = ["ProviderOperationPayload"]
