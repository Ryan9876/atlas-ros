from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from atlas_ros.intelligence.decision import (
    DecisionOutcome,
    GovernedDecisionPipeline,
)
from atlas_ros.intelligence.inference import (
    GovernedInferenceEngine,
    InferenceOutcome,
    InferenceRequest,
)
from atlas_ros.intelligence.reasoning import OptionAssessment, ReasoningOutcome, ReasoningRequest
from atlas_ros.intelligence.record_store import (
    SQLiteIntelligenceRecordStore,
)
from atlas_ros.intelligence.records import RecordRef


@dataclass(frozen=True)
class IntelligenceState:
    """Immutable results produced by each completed intelligence stage."""

    inference: InferenceOutcome | None = None
    reasoning: ReasoningOutcome | None = None
    decision: DecisionOutcome | None = None

    def __post_init__(self) -> None:
        if self.decision is not None and self.reasoning is None:
            raise ValueError("decision state requires a reasoning outcome")
        if self.decision is not None and self.decision.reasoning != self.reasoning:
            raise ValueError("decision outcome must contain the state reasoning outcome")

    @property
    def has_inference(self) -> bool:
        return self.inference is not None

    @property
    def has_reasoning(self) -> bool:
        return self.reasoning is not None

    @property
    def has_decision(self) -> bool:
        return self.decision is not None

    @property
    def completed(self) -> bool:
        return self.has_reasoning and self.has_decision


@dataclass(frozen=True)
class IntelligenceOutcome:
    """Complete immutable result of one orchestrated intelligence request."""

    request: ReasoningRequest
    state: IntelligenceState

    @property
    def inference(self) -> InferenceOutcome | None:
        return self.state.inference

    @property
    def reasoning(self) -> ReasoningOutcome | None:
        return self.state.reasoning

    @property
    def decision(self) -> DecisionOutcome | None:
        return self.state.decision

    @property
    def completed(self) -> bool:
        return self.state.completed


class IntelligenceOrchestrator:
    """Coordinates the complete intelligence workflow."""

    def __init__(
        self,
        record_store: SQLiteIntelligenceRecordStore,
        *,
        inference_engine: GovernedInferenceEngine | None = None,
        decision_pipeline: GovernedDecisionPipeline | None = None,
    ) -> None:
        self.record_store = record_store
        self.inference_engine = (
            inference_engine
            or GovernedInferenceEngine(record_store)
        )
        self.decision_pipeline = (
            decision_pipeline
            or GovernedDecisionPipeline(record_store)
        )

    def run(
        self,
        request: ReasoningRequest,
        *,
        policy_refs: tuple[RecordRef, ...],
        inference: InferenceRequest | None = None,
        created_at: datetime | None = None,
    ) -> IntelligenceOutcome:
        """Execute the governed intelligence workflow."""

        timestamp = created_at or datetime.now(UTC)

        inference_outcome: InferenceOutcome | None = None
        effective_request = request

        if inference is not None:
            known_options = {option.option for option in request.options}
            unknown_targets = sorted(set(inference.target_options) - known_options)
            if unknown_targets:
                raise ValueError(
                    "inference target options are not present in the reasoning request: "
                    + ", ".join(unknown_targets)
                )
            inference_outcome = self.inference_engine.infer(
                rule_ref=inference.rule_ref,
                premise_refs=inference.premise_refs,
                conclusion_statement=inference.conclusion_statement,
                claim_type=inference.claim_type,
                created_at=timestamp,
            )

            self.record_store.append_many(
                (
                    inference_outcome.conclusion,
                    inference_outcome.trace,
                )
            )
            effective_request = self._attach_inference_conclusion(
                request,
                conclusion_ref=inference_outcome.conclusion.ref(),
                target_options=inference.target_options,
            )

        decision: DecisionOutcome = self.decision_pipeline.evaluate(
            effective_request,
            policy_refs=policy_refs,
            created_at=timestamp,
        )

        decision_records = (
            *((decision.recommendation,) if decision.recommendation is not None else ()),
            *decision.policy_evaluations,
            decision.decision,
        )
        self.record_store.append_many(decision_records)

        state = IntelligenceState(
            inference=inference_outcome,
            reasoning=decision.reasoning,
            decision=decision,
        )

        return IntelligenceOutcome(
            request=effective_request,
            state=state,
        )

    @staticmethod
    def _attach_inference_conclusion(
        request: ReasoningRequest,
        *,
        conclusion_ref: RecordRef,
        target_options: tuple[str, ...],
    ) -> ReasoningRequest:
        target_set = set(target_options)
        options = tuple(
            OptionAssessment(
                option=option.option,
                scores=option.scores,
                expected_benefit=option.expected_benefit,
                expected_risk=option.expected_risk,
                evidence_refs=option.evidence_refs,
                claim_refs=tuple(
                    dict.fromkeys(
                        (
                            *option.claim_refs,
                            *((conclusion_ref,) if option.option in target_set else ()),
                        )
                    )
                ),
            )
            for option in request.options
        )
        return request.model_copy(update={"options": options})
