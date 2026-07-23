from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from atlas_ros.intelligence.decision_governance import (
    GovernanceOutcome,
    GovernedDecisionEngine,
)
from atlas_ros.intelligence.reasoning import (
    GovernedReasoningEngine,
    ReasoningOutcome,
    ReasoningRequest,
)
from atlas_ros.intelligence.record_store import (
    SQLiteIntelligenceRecordStore,
)
from atlas_ros.intelligence.records import (
    DecisionDisposition,
    DecisionGovernanceRecord,
    PolicyEvaluationRecord,
    RecommendationRecord,
    RecordRef,
)


@dataclass(frozen=True)
class DecisionOutcome:
    """Complete result of reasoning followed by decision governance."""

    reasoning: ReasoningOutcome
    governance: GovernanceOutcome

    @property
    def recommendation(self) -> RecommendationRecord | None:
        """Return the recommendation produced by the reasoning stage."""

        return self.reasoning.recommendation

    @property
    def policy_evaluations(
        self,
    ) -> tuple[PolicyEvaluationRecord, ...]:
        """Return all policy evaluations produced by governance."""

        return self.governance.evaluations

    @property
    def decision(self) -> DecisionGovernanceRecord:
        """Return the final immutable governance decision record."""

        return self.governance.governance

    @property
    def disposition(self) -> DecisionDisposition:
        """Return the final governed decision disposition."""

        return self.decision.disposition

    @property
    def permitted(self) -> bool:
        """Return whether governance permits the recommendation."""

        return self.decision.permitted


class GovernedDecisionPipeline:
    """Run reasoning and decision governance as one deterministic pipeline."""

    def __init__(
        self,
        record_store: SQLiteIntelligenceRecordStore,
        *,
        reasoning_engine: GovernedReasoningEngine | None = None,
        governance_engine: GovernedDecisionEngine | None = None,
    ) -> None:
        self.record_store = record_store
        self.reasoning_engine = reasoning_engine or GovernedReasoningEngine(record_store)
        self.governance_engine = governance_engine or GovernedDecisionEngine(record_store)

    def evaluate(
        self,
        request: ReasoningRequest,
        *,
        policy_refs: tuple[RecordRef, ...],
        created_at: datetime | None = None,
    ) -> DecisionOutcome:
        """Run reasoning, then govern the resulting recommendation."""

        reasoning = self.reasoning_engine.evaluate(
            request,
            created_at=created_at,
        )

        governance = self.governance_engine.evaluate(
            reasoning_outcome=reasoning,
            context_ref=request.context_ref,
            policy_refs=policy_refs,
            created_at=created_at,
        )

        return DecisionOutcome(
            reasoning=reasoning,
            governance=governance,
        )
