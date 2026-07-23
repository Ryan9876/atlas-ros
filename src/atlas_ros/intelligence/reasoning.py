from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator

from atlas_ros.intelligence.claim_graph import (
    ClaimAssessmentEngine,
    ClaimConflict,
    ClaimRelation,
    OptionClaimGraphAssessment,
)
from atlas_ros.intelligence.evidence_graph import (
    EvidenceConflict,
    EvidenceGraphAnalyzer,
    EvidenceRelation,
    OptionEvidenceGraphAssessment,
)
from atlas_ros.intelligence.record_store import SQLiteIntelligenceRecordStore
from atlas_ros.intelligence.records import (
    AuthorityLevel,
    ClaimRecord,
    ContextSnapshot,
    EvidenceEnvelope,
    RecommendationOption,
    RecommendationRecord,
    RecordKind,
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
    claim_refs: tuple[RecordRef, ...] = ()

    @model_validator(mode="after")
    def validate_scores_and_references(self) -> OptionAssessment:
        if any(score < 0.0 or score > 1.0 for score in self.scores.values()):
            raise ValueError("option scores must be between 0.0 and 1.0")
        if any(ref.kind is not RecordKind.EVIDENCE for ref in self.evidence_refs):
            raise ValueError("option evidence_refs must reference evidence envelopes")
        if any(ref.kind is not RecordKind.CLAIM for ref in self.claim_refs):
            raise ValueError("option claim_refs must reference claim records")
        return self


class ReasoningRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    objective: str = Field(min_length=1)
    context_ref: RecordRef
    criteria: tuple[DecisionCriterion, ...] = Field(min_length=1)
    options: tuple[OptionAssessment, ...] = Field(min_length=2)
    evidence_relations: tuple[EvidenceRelation, ...] = ()
    claim_relations: tuple[ClaimRelation, ...] = ()
    minimum_evidence_confidence: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
    )
    minimum_recommendation_margin: float = Field(
        default=0.05,
        ge=0.0,
        le=1.0,
    )

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

        permitted_options = set(option_names)
        for evidence_relation in self.evidence_relations:
            if evidence_relation.target_option not in permitted_options:
                raise ValueError("evidence relations must target a request option")
        for claim_relation in self.claim_relations:
            if claim_relation.target_option not in permitted_options:
                raise ValueError("claim relations must target a request option")

        return self


class EvidenceAssessment(BaseModel):
    model_config = ConfigDict(frozen=True)

    evidence_ref: RecordRef
    authority_score: float = Field(ge=0.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0)
    usable: bool
    reason: str = Field(min_length=1)


class ClaimAssessment(BaseModel):
    model_config = ConfigDict(frozen=True)

    claim_ref: RecordRef
    confidence: float = Field(ge=0.0, le=1.0)
    usable: bool
    reason: str = Field(min_length=1)


class ScoredOption(BaseModel):
    model_config = ConfigDict(frozen=True)

    option: str
    utility: float = Field(ge=0.0, le=1.0)
    evidence_strength: float = Field(ge=0.0, le=1.0)
    claim_strength: float = Field(default=1.0, ge=0.0, le=1.0)
    graph_multiplier: float = Field(default=1.0, ge=0.0, le=1.0)
    adjusted_score: float = Field(ge=0.0, le=1.0)
    criterion_contributions: dict[str, float]


class ReasoningTrace(BaseModel):
    model_config = ConfigDict(frozen=True)

    objective: str
    evidence: tuple[EvidenceAssessment, ...]
    claims: tuple[ClaimAssessment, ...] = ()
    evidence_graph: tuple[OptionEvidenceGraphAssessment, ...] = ()
    claim_graph: tuple[OptionClaimGraphAssessment, ...] = ()
    conflicts: tuple[EvidenceConflict, ...] = ()
    claim_conflicts: tuple[ClaimConflict, ...] = ()
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
    """Deterministic evidence, claim-graph, and criteria reasoning engine."""

    def __init__(
        self,
        record_store: SQLiteIntelligenceRecordStore,
        graph_analyzer: EvidenceGraphAnalyzer | None = None,
        claim_analyzer: ClaimAssessmentEngine | None = None,
    ) -> None:
        self.record_store = record_store
        self.graph_analyzer = graph_analyzer or EvidenceGraphAnalyzer()
        self.claim_analyzer = claim_analyzer or ClaimAssessmentEngine()

    def evaluate(
        self,
        request: ReasoningRequest,
        *,
        created_at: datetime | None = None,
    ) -> ReasoningOutcome:
        context = self.record_store.resolve(request.context_ref)
        if not isinstance(context, ContextSnapshot):
            raise ValueError("context_ref must resolve to ContextSnapshot")

        assessments: dict[RecordRef, EvidenceAssessment] = {}
        evidence_records: dict[RecordRef, EvidenceEnvelope] = {}
        claim_assessments: dict[RecordRef, ClaimAssessment] = {}
        claim_records: dict[RecordRef, ClaimRecord] = {}

        option_evidence_refs = tuple(
            dict.fromkeys(ref for option in request.options for ref in option.evidence_refs)
        )
        evidence_relation_refs = tuple(
            dict.fromkeys(
                ref
                for relation in request.evidence_relations
                for ref in (
                    relation.source_ref,
                    relation.target_ref,
                )
                if ref is not None
            )
        )
        option_claim_refs = tuple(
            dict.fromkeys(ref for option in request.options for ref in option.claim_refs)
        )
        claim_relation_refs = tuple(
            dict.fromkeys(
                ref
                for relation in request.claim_relations
                for ref in (
                    relation.source_ref,
                    relation.target_ref,
                )
                if ref is not None
            )
        )

        for ref in (*option_claim_refs, *claim_relation_refs):
            if ref in claim_assessments:
                continue

            record = self.record_store.resolve(ref)
            if not isinstance(record, ClaimRecord):
                raise ValueError("option and relation claim refs must resolve to ClaimRecord")

            usable = (
                record.validation_status is not ValidationStatus.REJECTED
                and record.confidence >= request.minimum_evidence_confidence
            )
            claim_assessments[ref] = ClaimAssessment(
                claim_ref=ref,
                confidence=record.confidence,
                usable=usable,
                reason=(
                    "usable validated claim" if usable else "rejected or below confidence threshold"
                ),
            )
            claim_records[ref] = record

        claim_evidence_refs = tuple(
            dict.fromkeys(ref for claim in claim_records.values() for ref in claim.evidence_refs)
        )

        for ref in (
            *option_evidence_refs,
            *evidence_relation_refs,
            *claim_evidence_refs,
        ):
            if ref in assessments:
                continue

            record = self.record_store.resolve(ref)
            if not isinstance(record, EvidenceEnvelope):
                raise ValueError(
                    "option, relation, and claim evidence refs must resolve to EvidenceEnvelope"
                )

            usable = (
                record.validation_status is not ValidationStatus.REJECTED
                and record.confidence >= request.minimum_evidence_confidence
            )
            assessments[ref] = EvidenceAssessment(
                evidence_ref=ref,
                authority_score=_AUTHORITY[record.source_authority],
                confidence=record.confidence,
                usable=usable,
                reason=(
                    "usable verified or qualified evidence"
                    if usable
                    else "rejected or below confidence threshold"
                ),
            )
            evidence_records[ref] = record

        option_names = tuple(option.option for option in request.options)

        graph_assessments, conflicts = self.graph_analyzer.analyze(
            option_names=option_names,
            evidence=evidence_records,
            relations=request.evidence_relations,
        )
        claim_graph_assessments, claim_conflicts = self.claim_analyzer.analyze(
            option_names=option_names,
            claims=claim_records,
            relations=request.claim_relations,
        )

        total_weight = sum(item.weight for item in request.criteria)
        scored: list[ScoredOption] = []

        for option in request.options:
            usable_evidence = [
                assessments[ref] for ref in option.evidence_refs if assessments[ref].usable
            ]
            evidence_strength = (
                sum(item.authority_score * item.confidence for item in usable_evidence)
                / len(usable_evidence)
                if usable_evidence
                else 0.0
            )

            usable_claims = [
                claim_assessments[ref] for ref in option.claim_refs if claim_assessments[ref].usable
            ]
            claim_strength = (
                sum(item.confidence for item in usable_claims) / len(usable_claims)
                if option.claim_refs and usable_claims
                else (0.0 if option.claim_refs else 1.0)
            )

            contributions: dict[str, float] = {}
            utility = 0.0
            for criterion in request.criteria:
                raw = option.scores[criterion.name]
                normalized = (
                    raw if criterion.direction is CriterionDirection.MAXIMIZE else 1.0 - raw
                )
                contribution = normalized * criterion.weight / total_weight
                contributions[criterion.name] = contribution
                utility += contribution

            evidence_graph = graph_assessments[option.option]
            claim_graph = claim_graph_assessments[option.option]
            graph_multiplier = evidence_graph.graph_multiplier * claim_graph.graph_multiplier
            adjusted = utility * evidence_strength * claim_strength * graph_multiplier

            scored.append(
                ScoredOption(
                    option=option.option,
                    utility=utility,
                    evidence_strength=evidence_strength,
                    claim_strength=claim_strength,
                    graph_multiplier=graph_multiplier,
                    adjusted_score=adjusted,
                    criterion_contributions=contributions,
                )
            )

        scored.sort(key=lambda item: (-item.adjusted_score, item.option))
        best, second = scored[0], scored[1]
        margin = best.adjusted_score - second.adjusted_score
        best_evidence_graph = graph_assessments[best.option]
        best_claim_graph = claim_graph_assessments[best.option]

        material_conflict = (
            best_evidence_graph.unresolved_conflict or best_claim_graph.unresolved_conflict
        )
        unmet_requirement = best_claim_graph.unmet_requirement
        conflict_penalty = 0.20 if material_conflict else 0.0
        requirement_penalty = 0.20 if unmet_requirement else 0.0

        uncertainty = min(
            1.0,
            1.0
            - best.evidence_strength
            + (1.0 - best.claim_strength) * 0.35
            + max(
                0.0,
                request.minimum_recommendation_margin - margin,
            )
            + conflict_penalty
            + requirement_penalty,
        )

        abstained = (
            best.evidence_strength == 0.0
            or best.claim_strength == 0.0
            or margin < request.minimum_recommendation_margin
            or material_conflict
            or unmet_requirement
        )

        graph_summary = (
            f" Evidence graph support "
            f"{best_evidence_graph.support_strength:.3f}, contradiction "
            f"{best_evidence_graph.contradiction_strength:.3f}, multiplier "
            f"{best_evidence_graph.graph_multiplier:.3f}. Claim graph "
            f"support {best_claim_graph.support_strength:.3f}, "
            f"contradiction "
            f"{best_claim_graph.contradiction_strength:.3f}, "
            f"qualification "
            f"{best_claim_graph.qualification_strength:.3f}, multiplier "
            f"{best_claim_graph.graph_multiplier:.3f}."
        )

        if abstained:
            explanation = (
                "No recommendation issued because usable support was "
                "absent, the leading option did not exceed the required "
                "decision margin, a material conflict remained unresolved, "
                "or a required claim was unmet." + graph_summary
            )
            trace = ReasoningTrace(
                objective=request.objective,
                evidence=tuple(assessments.values()),
                claims=tuple(claim_assessments.values()),
                evidence_graph=tuple(graph_assessments.values()),
                claim_graph=tuple(claim_graph_assessments.values()),
                conflicts=conflicts,
                claim_conflicts=claim_conflicts,
                ranked_options=tuple(scored),
                selected_option=None,
                abstained=True,
                explanation=explanation,
                uncertainty=uncertainty,
            )
            return ReasoningOutcome(
                trace=trace,
                recommendation=None,
            )

        selected = next(option for option in request.options if option.option == best.option)
        all_refs = tuple(
            dict.fromkeys(ref for option in request.options for ref in option.evidence_refs)
        )
        all_refs = tuple(dict.fromkeys((*all_refs, *claim_evidence_refs)))

        confidence = max(
            0.0,
            min(
                1.0,
                best.evidence_strength
                * best.claim_strength
                * best.graph_multiplier
                * (
                    0.5
                    + 0.5
                    * min(
                        1.0,
                        margin / 0.25,
                    )
                ),
            ),
        )
        rationale = (
            f"{best.option} ranked first with adjusted score "
            f"{best.adjusted_score:.3f}, a {margin:.3f} margin over "
            f"the next option, evidence strength "
            f"{best.evidence_strength:.3f}, and claim strength "
            f"{best.claim_strength:.3f}." + graph_summary
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
            claims=tuple(claim_assessments.values()),
            evidence_graph=tuple(graph_assessments.values()),
            claim_graph=tuple(claim_graph_assessments.values()),
            conflicts=conflicts,
            claim_conflicts=claim_conflicts,
            ranked_options=tuple(scored),
            selected_option=best.option,
            abstained=False,
            explanation=rationale,
            uncertainty=uncertainty,
        )
        return ReasoningOutcome(
            trace=trace,
            recommendation=recommendation,
        )

    @staticmethod
    def decision_quality(trace: ReasoningTrace) -> float:
        if trace.abstained:
            return max(0.0, 1.0 - trace.uncertainty) * 0.5

        top = trace.ranked_options[0]
        explanation_score = 1.0 if trace.explanation else 0.0
        evidence_conflict_score = (
            1.0 if not any(conflict.resolved_by is None for conflict in trace.conflicts) else 0.5
        )
        claim_conflict_score = (
            1.0
            if not any(conflict.resolved_by is None for conflict in trace.claim_conflicts)
            else 0.5
        )
        return min(
            1.0,
            0.40 * top.adjusted_score
            + 0.25 * (1.0 - trace.uncertainty)
            + 0.20 * explanation_score
            + 0.075 * evidence_conflict_score
            + 0.075 * claim_conflict_score,
        )
