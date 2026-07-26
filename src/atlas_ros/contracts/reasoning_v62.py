from __future__ import annotations

from typing import Literal

from pydantic import ConfigDict, Field, model_validator

from .domain_v62 import DomainKnowledgeContextV62
from .v62 import ClarificationStatus, EnhancedReasoningPackage


class EnhancedReasoningPackageV62(EnhancedReasoningPackage):
    """Complete v6.2 reasoning contract with one coherent routing conclusion."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    architecture_version: Literal["6.2"] = "6.2"
    classification: str = Field(min_length=1, max_length=100)
    destination: str = Field(min_length=1, max_length=200)
    responsibility_domain: str = Field(min_length=1, max_length=100)
    workstream: str = Field(min_length=1, max_length=200)
    planning_model: str = Field(min_length=1, max_length=200)
    planning_model_confidence: float = Field(ge=0, le=1)
    domain_knowledge_context: DomainKnowledgeContextV62
    requires_human_decision: bool = False

    @model_validator(mode="after")
    def validate_coherent_metadata(self) -> EnhancedReasoningPackageV62:
        expected_destination = {
            "action": "action_records",
            "project": "portfolio_projects",
            "delegated_work": "delegated_work",
            "risk": "risks_and_blockers",
            "decision": "decision_log",
            "reference": "reference",
            "needs_clarification": "universal_inbox",
        }.get(self.classification)
        if expected_destination is not None and self.destination != expected_destination:
            raise ValueError("classification and destination must resolve to one route")
        unresolved = (
            self.responsibility_domain == "unresolved"
            or self.workstream == "Needs Clarification"
        )
        if self.planning_model_confidence >= 0.85 and unresolved:
            raise ValueError(
                "high-confidence planning cannot coexist with unresolved routing metadata"
            )
        clarification_review = self.clarification.status in {
            ClarificationStatus.REQUIRED,
            ClarificationStatus.HUMAN_REVIEW_REQUIRED,
        }
        if self.requires_human_decision != clarification_review:
            raise ValueError("human-decision state must match clarification decision")
        if self.requires_human_decision and self.projection.projected_node_ids:
            raise ValueError("human-review reasoning cannot project execution work")
        if self.domain_knowledge_context.selection.requested_domain != (
            self.canonical_intent.domain
        ):
            raise ValueError("domain context must match canonical intent domain")
        return self
