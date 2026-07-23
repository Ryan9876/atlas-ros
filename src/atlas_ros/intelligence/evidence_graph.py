from __future__ import annotations

from collections import defaultdict
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator

from atlas_ros.intelligence.records import (
    AuthorityLevel,
    EvidenceEnvelope,
    RecordRef,
    ValidationStatus,
)


class EvidenceRelationType(StrEnum):
    SUPPORTS = "supports"
    CONTRADICTS = "contradicts"
    QUALIFIES = "qualifies"
    SUPERSEDES = "supersedes"


class EvidenceRelation(BaseModel):
    model_config = ConfigDict(frozen=True)

    source_ref: RecordRef
    relation: EvidenceRelationType
    target_option: str = Field(min_length=1)
    target_ref: RecordRef | None = None
    rationale: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_target(self) -> EvidenceRelation:
        if self.relation is EvidenceRelationType.SUPERSEDES and self.target_ref is None:
            raise ValueError("supersedes relations require target_ref")
        return self


class OptionEvidenceGraphAssessment(BaseModel):
    model_config = ConfigDict(frozen=True)

    option: str
    support_strength: float = Field(ge=0.0, le=1.0)
    contradiction_strength: float = Field(ge=0.0, le=1.0)
    qualification_strength: float = Field(ge=0.0, le=1.0)
    graph_multiplier: float = Field(ge=0.0, le=1.0)
    unresolved_conflict: bool
    supporting_refs: tuple[RecordRef, ...] = ()
    contradicting_refs: tuple[RecordRef, ...] = ()
    qualifying_refs: tuple[RecordRef, ...] = ()


class EvidenceConflict(BaseModel):
    model_config = ConfigDict(frozen=True)

    option: str
    supporting_ref: RecordRef
    contradicting_ref: RecordRef
    resolved_by: RecordRef | None = None
    explanation: str = Field(min_length=1)


_AUTHORITY_SCORE: dict[AuthorityLevel, float] = {
    AuthorityLevel.PRIMARY: 1.00,
    AuthorityLevel.AUTHORITATIVE_APPLICATION: 0.95,
    AuthorityLevel.GOVERNED_INTERNAL: 0.85,
    AuthorityLevel.USER_PROVIDED: 0.75,
    AuthorityLevel.INFERRED: 0.45,
    AuthorityLevel.UNVERIFIED: 0.20,
}

_VALIDATION_SCORE: dict[ValidationStatus, float] = {
    ValidationStatus.VERIFIED: 1.00,
    ValidationStatus.PARTIAL: 0.72,
    ValidationStatus.UNVERIFIED: 0.35,
    ValidationStatus.REJECTED: 0.00,
}


class EvidenceGraphAnalyzer:
    """Evaluates explicit support, contradiction, qualification, and precedence."""

    def analyze(
        self,
        *,
        option_names: tuple[str, ...],
        evidence: dict[RecordRef, EvidenceEnvelope],
        relations: tuple[EvidenceRelation, ...],
    ) -> tuple[
        dict[str, OptionEvidenceGraphAssessment],
        tuple[EvidenceConflict, ...],
    ]:
        by_option: dict[str, list[EvidenceRelation]] = defaultdict(list)
        superseded: set[RecordRef] = set()

        for relation in relations:
            if relation.target_option not in option_names:
                raise ValueError(
                    f"evidence relation targets unknown option {relation.target_option!r}"
                )
            if relation.source_ref not in evidence:
                raise ValueError("relation source_ref must resolve to evidence")
            if relation.target_ref is not None and relation.target_ref not in evidence:
                raise ValueError("relation target_ref must resolve to evidence")

            by_option[relation.target_option].append(relation)
            if (
                relation.relation is EvidenceRelationType.SUPERSEDES
                and relation.target_ref is not None
            ):
                superseded.add(relation.target_ref)

        assessments: dict[str, OptionEvidenceGraphAssessment] = {}
        conflicts: list[EvidenceConflict] = []

        for option in option_names:
            option_relations = by_option.get(option, [])
            supporting = tuple(
                relation.source_ref
                for relation in option_relations
                if relation.relation is EvidenceRelationType.SUPPORTS
                and relation.source_ref not in superseded
            )
            contradicting = tuple(
                relation.source_ref
                for relation in option_relations
                if relation.relation is EvidenceRelationType.CONTRADICTS
                and relation.source_ref not in superseded
            )
            qualifying = tuple(
                relation.source_ref
                for relation in option_relations
                if relation.relation is EvidenceRelationType.QUALIFIES
                and relation.source_ref not in superseded
            )

            support_strength = self._aggregate_strength(supporting, evidence)
            contradiction_strength = self._aggregate_strength(
                contradicting,
                evidence,
            )
            qualification_strength = self._aggregate_strength(
                qualifying,
                evidence,
            )

            option_conflicts = self._detect_conflicts(
                option=option,
                supporting=supporting,
                contradicting=contradicting,
                superseded=superseded,
                evidence=evidence,
            )
            conflicts.extend(option_conflicts)

            unresolved_conflict = any(conflict.resolved_by is None for conflict in option_conflicts)

            if not option_relations:
                graph_multiplier = 1.0
            else:
                graph_multiplier = self._bounded(
                    0.50
                    + 0.50 * support_strength
                    - 0.65 * contradiction_strength
                    - 0.20 * qualification_strength
                )

            assessments[option] = OptionEvidenceGraphAssessment(
                option=option,
                support_strength=support_strength,
                contradiction_strength=contradiction_strength,
                qualification_strength=qualification_strength,
                graph_multiplier=graph_multiplier,
                unresolved_conflict=unresolved_conflict,
                supporting_refs=supporting,
                contradicting_refs=contradicting,
                qualifying_refs=qualifying,
            )

        return assessments, tuple(conflicts)

    def _detect_conflicts(
        self,
        *,
        option: str,
        supporting: tuple[RecordRef, ...],
        contradicting: tuple[RecordRef, ...],
        superseded: set[RecordRef],
        evidence: dict[RecordRef, EvidenceEnvelope],
    ) -> tuple[EvidenceConflict, ...]:
        conflicts: list[EvidenceConflict] = []

        for supporting_ref in supporting:
            for contradicting_ref in contradicting:
                supporting_record = evidence[supporting_ref]
                contradicting_record = evidence[contradicting_ref]

                support_strength = self._record_strength(supporting_record)
                contradiction_strength = self._record_strength(contradicting_record)

                resolved_by: RecordRef | None = None
                if supporting_ref in superseded:
                    resolved_by = contradicting_ref
                elif (
                    contradicting_ref in superseded
                    or support_strength > contradiction_strength + 0.10
                ):
                    resolved_by = supporting_ref
                elif contradiction_strength > support_strength + 0.10:
                    resolved_by = contradicting_ref

                explanation = (
                    f"Conflicting evidence for {option}: support strength "
                    f"{support_strength:.3f}, contradiction strength "
                    f"{contradiction_strength:.3f}."
                )
                if resolved_by is not None:
                    explanation += (
                        " The conflict was resolved by authority, validation, "
                        "confidence, or supersession precedence."
                    )
                else:
                    explanation += " The conflict remains unresolved."

                conflicts.append(
                    EvidenceConflict(
                        option=option,
                        supporting_ref=supporting_ref,
                        contradicting_ref=contradicting_ref,
                        resolved_by=resolved_by,
                        explanation=explanation,
                    )
                )

        return tuple(conflicts)

    def _aggregate_strength(
        self,
        refs: tuple[RecordRef, ...],
        evidence: dict[RecordRef, EvidenceEnvelope],
    ) -> float:
        if not refs:
            return 0.0

        strengths = tuple(
            self._record_strength(evidence[ref])
            for ref in refs
            if evidence[ref].validation_status is not ValidationStatus.REJECTED
        )
        if not strengths:
            return 0.0

        strongest = max(strengths)
        corroboration_bonus = min(0.15, 0.05 * (len(strengths) - 1))
        return self._bounded(strongest + corroboration_bonus)

    @staticmethod
    def _record_strength(record: EvidenceEnvelope) -> float:
        return max(
            0.0,
            min(
                1.0,
                _AUTHORITY_SCORE[record.source_authority]
                * _VALIDATION_SCORE[record.validation_status]
                * record.confidence,
            ),
        )

    @staticmethod
    def _bounded(value: float) -> float:
        return max(0.0, min(1.0, value))
