"""Compiled, schema-validated operational-awareness policy."""

from __future__ import annotations

from importlib.resources import files
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

from atlas_ros.contracts.digests import sha256_digest
from atlas_ros.contracts.operational_awareness import AtlasCommandType, EffectiveWorkState


class PolicyModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class FreshnessThresholds(PolicyModel):
    current: int = Field(ge=0)
    aging: int = Field(gt=0)
    stale: int = Field(gt=0)

    @model_validator(mode="after")
    def ordered(self) -> FreshnessThresholds:
        if not self.current < self.aging < self.stale:
            raise ValueError("freshness thresholds must be strictly increasing")
        return self


class ConfidencePolicy(PolicyModel):
    base: float = Field(ge=0, le=1)
    missing_material_penalty: float = Field(ge=0, le=1)
    contradiction_penalty: float = Field(ge=0, le=1)
    stale_penalty: float = Field(ge=0, le=1)
    unverified_penalty: float = Field(ge=0, le=1)


class CompletionPolicy(PolicyModel):
    require_definition_of_done: bool
    require_completion_evidence: bool
    require_closed_children: bool
    require_approval_when_declared: bool


class BriefPolicy(PolicyModel):
    item_budget: int = Field(ge=1, le=100)
    critical_priority: int = Field(ge=1, le=4)
    deduplicate_by_record: bool


class ContextPolicy(PolicyModel):
    evidence_limit: int = Field(ge=1, le=100)
    stale_warning_days: int = Field(ge=1)


class HygienePolicy(PolicyModel):
    protected_record_types: tuple[str, ...]
    max_active_delegated_checkpoints: int = Field(ge=1, le=4)


class CommandPolicy(PolicyModel):
    allowed_commands: tuple[AtlasCommandType, ...]
    max_object_count: int = Field(ge=1, le=25)
    missing_checkpoint_behavior: str
    preserve_parent_outcome: bool
    require_readback: bool
    replay_safe: bool

    @model_validator(mode="after")
    def validate_boundaries(self) -> CommandPolicy:
        if not self.preserve_parent_outcome or not self.require_readback or not self.replay_safe:
            raise ValueError("command policy cannot weaken parent, readback, or replay controls")
        if self.missing_checkpoint_behavior not in {"undated_follow_up", "reject"}:
            raise ValueError("unsupported missing-checkpoint behavior")
        return self


class OperationalAwarenessPolicy(PolicyModel):
    schema_version: str
    policy_id: str
    lifecycle: str
    state_mappings: dict[str, EffectiveWorkState]
    authority_precedence: tuple[str, ...]
    freshness_days: FreshnessThresholds
    confidence: ConfidencePolicy
    completion: CompletionPolicy
    brief: BriefPolicy
    context: ContextPolicy
    hygiene: HygienePolicy
    command: CommandPolicy
    policy_digest: str = Field(pattern=r"^[0-9a-f]{64}$")

    @classmethod
    def compile(cls, payload: dict[str, Any]) -> OperationalAwarenessPolicy:
        if payload.get("schema_version") != "1.0":
            raise ValueError("unsupported operational-awareness policy schema")
        if payload.get("policy_id") != "atlas.operational-awareness.v1":
            raise ValueError("unexpected operational-awareness policy identity")
        if payload.get("lifecycle") != "active":
            raise ValueError("operational-awareness policy must be active")
        values = dict(payload)
        values["policy_digest"] = sha256_digest(payload)
        return cls.model_validate(values)

    def verify_digest(self) -> bool:
        return self.policy_digest == sha256_digest(
            self.model_dump(mode="json", exclude={"policy_digest"})
        )


def load_operational_awareness_policy(path: Path | None = None) -> OperationalAwarenessPolicy:
    source = path or Path(str(files("atlas_ros.data").joinpath("operational-awareness.yaml")))
    loaded = yaml.safe_load(source.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError("operational-awareness policy must be a mapping")
    policy = OperationalAwarenessPolicy.compile(loaded)
    if not policy.verify_digest():
        raise ValueError("operational-awareness policy digest mismatch")
    return policy
