from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .models import deterministic_digest
from .v62 import EvidenceReference, MemoryApprovalState


class DomainKnowledgePackV62(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    contract_version: Literal[1] = 1
    pack_id: str = Field(min_length=1, max_length=200)
    version: str = Field(min_length=1, max_length=100)
    domain: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=2_000)
    terminology: tuple[str, ...] = ()
    planning_facts: tuple[str, ...] = ()
    provider_free: Literal[True] = True
    execution_authority: Literal[False] = False
    approval_state: MemoryApprovalState = MemoryApprovalState.APPROVED
    provenance: tuple[EvidenceReference, ...] = ()
    pack_digest: str = Field(min_length=64, max_length=64)

    @model_validator(mode="after")
    def validate_pack(self) -> DomainKnowledgePackV62:
        expected = deterministic_digest(
            self.model_dump(mode="json", exclude={"pack_digest"})
        )
        if self.pack_digest != expected:
            raise ValueError("domain-pack digest verification failed")
        return self


class DomainKnowledgeSelectionV62(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    contract_version: Literal[1] = 1
    requested_domain: str = Field(min_length=1, max_length=200)
    selected_pack_id: str = Field(min_length=1, max_length=200)
    selected_pack_version: str = Field(min_length=1, max_length=100)
    confidence: float = Field(ge=0, le=1)
    sufficient: bool
    missing_requirements: tuple[str, ...] = ()
    evidence: tuple[EvidenceReference, ...] = ()
    selection_digest: str = Field(min_length=64, max_length=64)

    @model_validator(mode="after")
    def validate_selection(self) -> DomainKnowledgeSelectionV62:
        if self.sufficient and self.missing_requirements:
            raise ValueError("sufficient domain selection cannot retain missing requirements")
        if self.sufficient != (self.confidence >= 0.75 and not self.missing_requirements):
            raise ValueError("domain sufficiency contradicts confidence or missing requirements")
        expected = deterministic_digest(
            self.model_dump(mode="json", exclude={"selection_digest"})
        )
        if self.selection_digest != expected:
            raise ValueError("domain-selection digest verification failed")
        return self


class DomainKnowledgeContextV62(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    selection: DomainKnowledgeSelectionV62
    facts: dict[str, Any] = Field(default_factory=dict)
    terminology: tuple[str, ...] = ()
    context_digest: str = Field(min_length=64, max_length=64)

    @model_validator(mode="after")
    def validate_context(self) -> DomainKnowledgeContextV62:
        expected = deterministic_digest(
            self.model_dump(mode="json", exclude={"context_digest"})
        )
        if self.context_digest != expected:
            raise ValueError("domain-context digest verification failed")
        return self
