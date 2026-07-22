from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator

from atlas_ros.intelligence.record_store import SQLiteIntelligenceRecordStore
from atlas_ros.intelligence.records import (
    AuthorityLevel,
    ContextSnapshot,
    EvidenceEnvelope,
    RecommendationOption,
    RecommendationRecord,
    RecordRef,
    ValidationStatus,
)


class CriterionDirection(StrEnum):
    MAXIMIZE = "maximize"
    MINIMIZE = "minimize"


class DecisionCriterion(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str = Field(min_length=1)
    weight: float = Field(gt=0.0)
    direction: CriterionDirection = CriterionDirection.MAXIMIZE


class OptionAssessment(BaseModel):
    model_config = ConfigDict(frozen=True)

    option: str = Field(min_length=1)
    scores: dict[str, float]
    expected_benefit: str = Field(min_length=1)
    expected_risk: str = Field(min_length=1)
    evidence_refs: tuple[RecordRef, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_scores(self) -> OptionAssessment:
        if any(score < 0.0 or score > 1.0 for score in self.scores.values()):
            raise ValueError("option scores must be between 0.0 and 1.0")
        return self


class ReasoningRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    objective: str = Field(min_length=1)
    context_ref: RecordRef
    criteria: tuple[DecisionCriterion, ...] = Field(min_length=1)
    options: tuple[OptionAssessment, ...] = Field(min_length=2)
    minimum_evidence_confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    minimum_recommendation_margin: float = Field(default=0.05, ge=0.0, le=1.0)

    @model_validator(mode="after")
    def validate_request(self) -> ReasoningRequest:
        names = [criterion.name for criterion in self.criteria]
        if len(names) != len(set(names)):
            raise ValueError("criterion names must be unique")
        option_names = [option.option for option in self.options]
        if len(option_names) != len(set(option_names)):
            raise ValueError("option names must be unique")
        required = set(names)
        for option in self.options:
            if set(option.scores) != required:
                raise ValueError("every option must score every criterion exactly once")
        return self


class EvidenceAssessment(BaseModel):
    model_config = ConfigDict(frozen=True)

    evidence_ref: RecordRef
    authority_score: float = Field(ge=0.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0)
    usable: bool
    reason: str = Field(min_length=1)


class ScoredOption(BaseModel):
    model_config = ConfigDict(frozen=True)

    option: str
    utility: float = Field(ge=0.0, le=1.0)
    evidence_strength: float = Field(ge=0.0, le=1.0)
    adjusted_score: float = Field(ge=0.0, le=1.0)
    criterion_contributions: dict[str, float]


class ReasoningTrace(BaseModel):
    model_config = ConfigDict(frozen=True)

    objective: str
    evidence: tuple[EvidenceAssessment, ...]
    ranked_options: tuple[ScoredOption, ...]
    selected_option: str | None
    abstained: bool
    explanation: str
    uncertainty: float = Field(ge=0.0, le=1.0)


@dataclass(frozen=True)
class ReasoningOutcome:
    trace: ReasoningTrace
    recommendation: RecommendationRecord | None


_AUTHORITY = {
    AuthorityLevel.PRIMARY: 1.0,
    AuthorityLevel.AUTHORITATIVE_APPLICATION: 0.95,
    AuthorityLevel.GOVERNED_INTERNAL: 0.85,
    AuthorityLevel.USER_PROVIDED: 0.75,
    AuthorityLevel.INFERRED: 0.45,
    AuthorityLevel.UNVERIFIED: 0.20,
}


class GovernedReasoningEngine:
    """Deterministic, evidence-first multi-criteria recommendation engine."""

    def __init__(self, record_store: SQLiteIntelligenceRecordStore) -> None:
        self.record_store = record_store

    def evaluate(self, request: ReasoningRequest, *, created_at: datetime | None = None) -> ReasoningOutcome:
        context = self.record_store.resolve(request.context_ref)
        if not isinstance(context, ContextSnapshot):
            raise ValueError("context_ref must resolve to ContextSnapshot")
        assessments: dict[RecordRef, EvidenceAssessment] = {}
        evidence_records: dict[RecordRef, EvidenceEnvelope] = {}
        for option in request.options:
            for ref in option.evidence_refs:
                if ref in assessments:
                    continue
                record = self.record_store.resolve(ref)
                if not isinstance(record, EvidenceEnvelope):
                    raise ValueError("option evidence_refs must resolve to EvidenceEnvelope")
                usable = (
                    record.validation_status is not ValidationStatus.REJECTED
                    and record.confidence >= request.minimum_evidence_confidence
                )
                reason = "usable verified or qualified evidence" if usable else "rejected or below confidence threshold"
                assessments[ref] = EvidenceAssessment(
                    evidence_ref=ref,
                    authority_score=_AUTHORITY[record.source_authority],
                    confidence=record.confidence,
                    usable=usable,
                    reason=reason,
                )
                evidence_records[ref] = record
        total_weight = sum(item.weight for item in request.criteria)
        scored: list[ScoredOption] = []
        for option in request.options:
            usable_assessments = [
                assessments[ref]
                for ref in option.evidence_refs
                if assessments[ref].usable
            ]
            evidence_strength = (
                sum(
                    item.authority_score * item.confidence
                    for item in usable_assessments
                )
                / len(usable_assessments)
                if usable_assessments
                else 0.0
            )
            contributions: dict[str, float] = {}
            utility = 0.0
            for criterion in request.criteria:
                raw = option.scores[criterion.name]
                normalized = raw if criterion.direction is CriterionDirection.MAXIMIZE else 1.0 - raw
                contribution = normalized * criterion.weight / total_weight
                contributions[criterion.name] = contribution
                utility += contribution
            adjusted = utility * evidence_strength
            scored.append(
                ScoredOption(
                    option=option.option,
                    utility=utility,
                    evidence_strength=evidence_strength,
                    adjusted_score=adjusted,
                    criterion_contributions=contributions,
                )
            )
        scored.sort(key=lambda item: (-item.adjusted_score, item.option))
        best, second = scored[0], scored[1]
        margin = best.adjusted_score - second.adjusted_score
        uncertainty = min(1.0, 1.0 - best.evidence_strength + max(0.0, request.minimum_recommendation_margin - margin))
        abstained = best.evidence_strength == 0.0 or margin < request.minimum_recommendation_margin
        if abstained:
            explanation = (
                "No recommendation issued because usable evidence was absent or the leading option "
                "did not exceed the required decision margin."
            )
            trace = ReasoningTrace(
                objective=request.objective,
                evidence=tuple(assessments.values()),
                ranked_options=tuple(scored),
                selected_option=None,
                abstained=True,
                explanation=explanation,
                uncertainty=uncertainty,
            )
            return ReasoningOutcome(trace=trace, recommendation=None)
        selected = next(option for option in request.options if option.option == best.option)
        all_refs = tuple(dict.fromkeys(ref for option in request.options for ref in option.evidence_refs))
        confidence = max(0.0, min(1.0, best.evidence_strength * (0.5 + 0.5 * min(1.0, margin / 0.25))))
        rationale = (
            f"{best.option} ranked first with adjusted score {best.adjusted_score:.3f}, "
            f"a {margin:.3f} margin over the next option, and evidence strength "
            f"{best.evidence_strength:.3f}."
        )
        recommendation = RecommendationRecord(
            created_at=created_at or datetime.now(UTC),
            recommendation=best.option,
            alternatives=tuple(
                RecommendationOption(
                    option=option.option,
                    expected_benefit=option.expected_benefit,
                    expected_risk=option.expected_risk,
                )
                for option in request.options
            ),
            rationale=rationale,
            expected_benefit=selected.expected_benefit,
            expected_risk=selected.expected_risk,
            confidence=confidence,
            evidence_refs=all_refs,
            context_ref=request.context_ref,
        )
        trace = ReasoningTrace(
            objective=request.objective,
            evidence=tuple(assessments.values()),
            ranked_options=tuple(scored),
            selected_option=best.option,
            abstained=False,
            explanation=rationale,
            uncertainty=uncertainty,
        )
        return ReasoningOutcome(trace=trace, recommendation=recommendation)

    @staticmethod
    def decision_quality(trace: ReasoningTrace) -> float:
        if trace.abstained:
            return max(0.0, 1.0 - trace.uncertainty) * 0.5
        top = trace.ranked_options[0]
        explanation_score = 1.0 if trace.explanation else 0.0
        return min(1.0, 0.5 * top.adjusted_score + 0.3 * (1.0 - trace.uncertainty) + 0.2 * explanation_score)
