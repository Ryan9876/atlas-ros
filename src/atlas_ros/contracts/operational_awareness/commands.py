"""Explicit Atlas lifecycle command contracts."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import Field, model_validator

from atlas_ros.contracts.advisory_v1 import ConfidenceAssessment
from atlas_ros.contracts.digests import sha256_digest

from .base import AtlasCommandType, AuthoritativeSystem, DigestBoundModel
from .records import OperationalRecordRefV1


class CommandSourceRefV1(DigestBoundModel):
    digest_field = "source_digest"

    contract_id: Literal["atlas.command-source-ref"] = "atlas.command-source-ref"
    schema_version: Literal["1.0"] = "1.0"
    source_provider: AuthoritativeSystem
    source_task_id: str
    source_task_revision: str
    source_command_text: str
    parent_task_id: str | None = None
    source_digest: str = Field(pattern=r"^[0-9a-f]{64}$")

    @classmethod
    def create(cls, **values: Any) -> CommandSourceRefV1:
        return cls(source_digest=cls.compute_digest(values), **values)

    @model_validator(mode="after")
    def validate_digest(self) -> CommandSourceRefV1:
        if not self.verify_digest():
            raise ValueError("command source digest mismatch")
        return self


class AtlasCommandV1(DigestBoundModel):
    digest_field = "command_digest"
    digest_excluded_fields = frozenset({"idempotency_identity"})

    contract_id: Literal["atlas.command"] = "atlas.command"
    schema_version: Literal["1.0"] = "1.0"
    command_type: AtlasCommandType
    source: CommandSourceRefV1
    subject: str | None = None
    fields: dict[str, str] = Field(default_factory=dict)
    command_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    idempotency_identity: str

    @classmethod
    def create(cls, **values: Any) -> AtlasCommandV1:
        digest = cls.compute_digest(values)
        return cls(command_digest=digest, idempotency_identity=f"atlas-command:{digest}", **values)

    @model_validator(mode="after")
    def validate_command(self) -> AtlasCommandV1:
        if self.idempotency_identity != f"atlas-command:{self.command_digest}":
            raise ValueError("command idempotency identity mismatch")
        if not self.verify_digest():
            raise ValueError("command digest mismatch")
        return self


class CommandInterpretationV1(DigestBoundModel):
    digest_field = "interpretation_digest"

    contract_id: Literal["atlas.command-interpretation"] = "atlas.command-interpretation"
    schema_version: Literal["1.0"] = "1.0"
    command: AtlasCommandV1
    parent_outcome: OperationalRecordRefV1 | None = None
    affected_notion_record: OperationalRecordRefV1 | None = None
    responsible_party: str | None = None
    accountable_party: str | None = None
    expected_outcome: str | None = None
    completion_criteria: tuple[str, ...] = ()
    next_checkpoint: str | None = None
    next_ryan_owned_action: str | None = None
    confidence: ConfidenceAssessment
    ambiguity: tuple[str, ...] = ()
    blockers: tuple[str, ...] = ()
    interpretation_digest: str = Field(pattern=r"^[0-9a-f]{64}$")

    @classmethod
    def create(cls, **values: Any) -> CommandInterpretationV1:
        return cls(interpretation_digest=cls.compute_digest(values), **values)

    @model_validator(mode="after")
    def validate_interpretation(self) -> CommandInterpretationV1:
        if self.ambiguity and not self.blockers:
            raise ValueError("ambiguous interpretation must fail closed with blockers")
        if not self.verify_digest():
            raise ValueError("command interpretation digest mismatch")
        return self
