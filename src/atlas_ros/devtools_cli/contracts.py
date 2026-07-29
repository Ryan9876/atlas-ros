"""Versioned contracts for governed feature delivery."""

from __future__ import annotations

import hashlib
import json
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class FeatureCategory(StrEnum):
    ADVISORY = "advisory"
    CLASSIFICATION = "classification"
    PLANNING = "planning"
    EXECUTION_INTENT = "execution_intent"
    PROVIDER_INTEGRATION = "provider_integration"
    MIGRATION = "migration"
    RECONCILIATION = "reconciliation"
    RELEASE_TOOLING = "release_tooling"
    DEVELOPMENT_TOOLING = "development_tooling"


class AuthorityDeclaration(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    provider_writes: str = "none"
    production_migration: str = "none"
    promotion: str = "separately_authorized"

    @model_validator(mode="after")
    def reject_implicit_authority(self) -> "AuthorityDeclaration":
        prohibited = {"authorized", "automatic", "unattended"}
        if self.provider_writes in prohibited or self.production_migration in prohibited:
            raise ValueError("feature contracts cannot grant production authority")
        return self


class FeatureImplementationContractV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    schema_version: str = "feature-contract-v1"
    feature_id: str = Field(min_length=3)
    feature_name: str = Field(min_length=3)
    target_release: str
    category: FeatureCategory
    business_objective: str
    user_visible_outcome: str
    inputs: tuple[str, ...] = ()
    outputs: tuple[str, ...] = ()
    authoritative_systems: tuple[str, ...] = ()
    affected_capabilities: tuple[str, ...] = ()
    affected_contracts: tuple[str, ...] = ()
    affected_policies: tuple[str, ...] = ()
    provider_read_requirements: tuple[str, ...] = ()
    authority: AuthorityDeclaration = AuthorityDeclaration()
    migration_classification: str = "none"
    security_classification: str = "internal"
    compatibility_requirements: tuple[str, ...] = ()
    invariants: tuple[str, ...]
    prohibited_behaviors: tuple[str, ...]
    decisions_reserved_for_ryan: tuple[str, ...] = ()
    required_scenario_categories: tuple[str, ...]
    acceptance_criteria: tuple[str, ...]
    performance_expectations: tuple[str, ...] = ()
    release_impact: str
    documentation_impact: str

    @model_validator(mode="after")
    def validate_category_obligations(self) -> "FeatureImplementationContractV1":
        if self.category in {FeatureCategory.EXECUTION_INTENT, FeatureCategory.PROVIDER_INTEGRATION}:
            required = {"idempotency", "provider_readback"}
            if not required.issubset(set(self.required_scenario_categories)):
                raise ValueError("execution/provider features require idempotency and provider_readback")
        if self.migration_classification != "none" and self.authority.production_migration == "none":
            raise ValueError("migration classification contradicts production_migration declaration")
        return self

    def digest(self) -> str:
        payload = self.model_dump(mode="json", exclude_none=True)
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha256(raw).hexdigest()

    def implementation_summary(self) -> dict[str, Any]:
        return {
            "feature_id": self.feature_id,
            "target_release": self.target_release,
            "category": self.category.value,
            "digest": self.digest(),
            "initial_validation_scope": sorted(set(self.affected_capabilities)),
            "reserved_decisions": list(self.decisions_reserved_for_ryan),
            "authorization_granted": False,
        }


class FeatureDefinitionOfDoneV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    schema_version: str = "feature-dod-v1"
    feature_id: str
    required_items: tuple[str, ...]
    evidence: dict[str, str] = {}

    def missing(self) -> tuple[str, ...]:
        return tuple(item for item in self.required_items if not self.evidence.get(item))


class ChangeImpactAssessmentV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    schema_version: str = "change-impact-v1"
    mode: str = "shadow"
    changed_paths: tuple[str, ...]
    affected_nodes: tuple[str, ...]
    transitive_effects: tuple[str, ...]
    risk_classification: str
    selected_validation: tuple[str, ...]
    broadened_validation: tuple[str, ...]
    workflow_selection: tuple[str, ...]
    full_history_required: bool
    clean_build_required: bool
    rationale: tuple[str, ...]
    impact_digest: str
    suppresses_mandatory_gates: bool = False

    @model_validator(mode="after")
    def enforce_shadow_safety(self) -> "ChangeImpactAssessmentV1":
        if self.mode != "shadow":
            raise ValueError("v7.4.0 impact analysis is shadow-only")
        if self.suppresses_mandatory_gates:
            raise ValueError("impact analysis cannot suppress mandatory gates")
        return self
