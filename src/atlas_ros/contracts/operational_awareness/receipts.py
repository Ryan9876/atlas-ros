"""Operational-awareness and command lifecycle receipts."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import Field, model_validator

from atlas_ros.contracts.digests import sha256_digest

from .base import DigestBoundModel


class AwarenessStageReceiptV1(DigestBoundModel):
    digest_field = "receipt_digest"

    contract_id: Literal["atlas.awareness-stage-receipt"] = "atlas.awareness-stage-receipt"
    schema_version: Literal["1.0"] = "1.0"
    stage: str
    input_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    output_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    provider_writes: int = Field(default=0, ge=0)
    receipt_digest: str = Field(pattern=r"^[0-9a-f]{64}$")

    @classmethod
    def create(cls, **values: Any) -> AwarenessStageReceiptV1:
        return cls(receipt_digest=cls.compute_digest(values), **values)

    @model_validator(mode="after")
    def validate_receipt(self) -> AwarenessStageReceiptV1:
        if self.provider_writes != 0:
            raise ValueError("operational-awareness stages cannot perform provider writes")
        if not self.verify_digest():
            raise ValueError("awareness stage receipt digest mismatch")
        return self


class OperationalAwarenessReceiptV1(DigestBoundModel):
    digest_field = "receipt_digest"

    contract_id: Literal["atlas.operational-awareness-receipt"] = (
        "atlas.operational-awareness-receipt"
    )
    schema_version: Literal["1.0"] = "1.0"
    snapshot_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    policy_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    stage_receipts: tuple[AwarenessStageReceiptV1, ...]
    provider_writes: int = Field(default=0, ge=0)
    replay_id: str
    receipt_digest: str = Field(pattern=r"^[0-9a-f]{64}$")

    @classmethod
    def create(cls, **values: Any) -> OperationalAwarenessReceiptV1:
        return cls(receipt_digest=cls.compute_digest(values), **values)

    @model_validator(mode="after")
    def validate_receipt(self) -> OperationalAwarenessReceiptV1:
        if self.provider_writes != 0 or any(
            stage.provider_writes != 0 for stage in self.stage_receipts
        ):
            raise ValueError("operational awareness receipt must prove zero provider writes")
        if not self.verify_digest():
            raise ValueError("operational awareness receipt digest mismatch")
        return self


class CommandExecutionReceiptV1(DigestBoundModel):
    digest_field = "receipt_digest"

    contract_id: Literal["atlas.command-execution-receipt"] = "atlas.command-execution-receipt"
    schema_version: Literal["1.0"] = "1.0"
    command_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    interpretation_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    lifecycle_plan_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    canonical_plan_digest: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    authorization_id: str | None = None
    operation_identities: tuple[str, ...] = ()
    readback_digests: tuple[str, ...] = ()
    provider_write_count: int = Field(default=0, ge=0)
    completion_state: str = "planned_not_executed"
    receipt_digest: str = Field(pattern=r"^[0-9a-f]{64}$")

    @classmethod
    def create(cls, **values: Any) -> CommandExecutionReceiptV1:
        return cls(receipt_digest=cls.compute_digest(values), **values)

    @model_validator(mode="after")
    def validate_receipt(self) -> CommandExecutionReceiptV1:
        if self.completion_state == "planned_not_executed" and self.provider_write_count != 0:
            raise ValueError("unexecuted command receipt cannot report provider writes")
        if not self.verify_digest():
            raise ValueError("command execution receipt digest mismatch")
        return self
