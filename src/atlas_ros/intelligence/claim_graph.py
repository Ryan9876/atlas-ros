from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator

from atlas_ros.intelligence.records import (
    ClaimRecord,
    RecordRef,
    ValidationStatus,
)


class ClaimRelationType(StrEnum):
    SUPPORTS = "supports"
    CONTRADICTS = "contradicts"
    QUALIFIES = "qualifies"
    REQUIRES = "requires"
    SUPERSEDES = "supersedes"


class ClaimRelation(BaseModel):
    model_config = ConfigDict(frozen=True)

    source_ref: RecordRef
    relation: ClaimRelationType
    target_option: str = Field(min_length=1)
    target_ref: RecordRef | None = None
    rationale: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_relation(self) -> ClaimRelation:
        if self.source_ref.kind.value != "claim_record":
            raise ValueError("claim relation source_ref must reference a claim record")

        if self.relation is ClaimRelationType.SUPERSEDES:
            if self.target_ref is None:
                raise ValueError("supersedes relations require target_ref")
            if self.target_ref.kind.value != "claim_record":
                raise ValueError("supersedes target_ref must reference a claim record")
        elif self.target_ref is not None:
            raise ValueError("target_ref is only valid for supersedes relations")

        return self


class ClaimConflict(BaseModel):
    model_config = ConfigDict(frozen=True)

    option: str
    supporting_ref: RecordRef
    contradicting_ref: RecordRef
    resolved_by: RecordRef | None = None
    rationale: str = Field(min_length=1)


class OptionClaimGraphAssessment(BaseModel):
    model_config = ConfigDict(frozen=True)

    option: str
    support_strength: float = Field(ge=0.0, le=1.0)
    contradiction_strength: float = Field(ge=0.0, le=1.0)
    qualification_strength: float = Field(ge=0.0, le=1.0)
    requirement_strength: float = Field(ge=0.0, le=1.0)
    graph_multiplier: float = Field(ge=0.0, le=1.0)
    supporting_refs: tuple[RecordRef, ...] = ()
    contradicting_refs: tuple[RecordRef, ...] = ()
    qualifying_refs: tuple[RecordRef, ...] = ()
    required_refs: tuple[RecordRef, ...] = ()
    unresolved_conflict: bool = False
    unmet_requirement: bool = False


class ClaimAssessmentEngine:
    """Deterministic claim-graph assessment and conflict resolution."""

    def analyze(
        self,
        *,
        option_names: tuple[str, ...],
        claims: dict[RecordRef, ClaimRecord],
        relations: tuple[ClaimRelation, ...],
    ) -> tuple[
        dict[str, OptionClaimGraphAssessment],
        tuple[ClaimConflict, ...],
    ]:
        superseded = {
            relation.target_ref
            for relation in relations
            if relation.relation is ClaimRelationType.SUPERSEDES and relation.target_ref is not None
        }

        assessments: dict[str, OptionClaimGraphAssessment] = {}
        conflicts: list[ClaimConflict] = []

        for option in option_names:
            option_relations = tuple(
                relation
                for relation in relations
                if relation.target_option == option
                and relation.relation is not ClaimRelationType.SUPERSEDES
                and relation.source_ref not in superseded
            )

            supporting_refs = self._refs_for(
                option_relations,
                ClaimRelationType.SUPPORTS,
            )
            contradicting_refs = self._refs_for(
                option_relations,
                ClaimRelationType.CONTRADICTS,
            )
            qualifying_refs = self._refs_for(
                option_relations,
                ClaimRelationType.QUALIFIES,
            )
            required_refs = self._refs_for(
                option_relations,
                ClaimRelationType.REQUIRES,
            )

            support_strength = self._aggregate_strength(
                supporting_refs,
                claims,
            )
            contradiction_strength = self._aggregate_strength(
                contradicting_refs,
                claims,
            )
            qualification_strength = self._aggregate_strength(
                qualifying_refs,
                claims,
            )
            requirement_strength = self._aggregate_strength(
                required_refs,
                claims,
            )

            unresolved_conflict = False
            for supporting_ref in supporting_refs:
                for contradicting_ref in contradicting_refs:
                    supporting = claims[supporting_ref]
                    contradicting = claims[contradicting_ref]

                    support_score = self._claim_strength(supporting)
                    contradiction_score = self._claim_strength(contradicting)
                    resolved_by: RecordRef | None = None

                    if supporting_ref in superseded:
                        resolved_by = contradicting_ref
                    elif (
                        contradicting_ref in superseded
                        or support_score > contradiction_score + 0.10
                    ):
                        resolved_by = supporting_ref
                    elif contradiction_score > support_score + 0.10:
                        resolved_by = contradicting_ref
                    else:
                        unresolved_conflict = True

                    conflicts.append(
                        ClaimConflict(
                            option=option,
                            supporting_ref=supporting_ref,
                            contradicting_ref=contradicting_ref,
                            resolved_by=resolved_by,
                            rationale=(
                                "Claim conflict resolved by confidence and validation strength."
                                if resolved_by is not None
                                else "Material claim conflict remains unresolved."
                            ),
                        )
                    )

            unmet_requirement = any(not self._claim_is_usable(claims[ref]) for ref in required_refs)

            positive = min(
                1.0,
                support_strength + 0.20 * qualification_strength + 0.10 * requirement_strength,
            )
            negative = min(
                1.0,
                contradiction_strength
                + (0.35 if unresolved_conflict else 0.0)
                + (0.40 if unmet_requirement else 0.0),
            )
            graph_multiplier = max(
                0.0,
                min(
                    1.0,
                    0.65 + 0.35 * positive - 0.55 * negative,
                ),
            )

            assessments[option] = OptionClaimGraphAssessment(
                option=option,
                support_strength=support_strength,
                contradiction_strength=contradiction_strength,
                qualification_strength=qualification_strength,
                requirement_strength=requirement_strength,
                graph_multiplier=graph_multiplier,
                supporting_refs=supporting_refs,
                contradicting_refs=contradicting_refs,
                qualifying_refs=qualifying_refs,
                required_refs=required_refs,
                unresolved_conflict=unresolved_conflict,
                unmet_requirement=unmet_requirement,
            )

        return assessments, tuple(conflicts)

    @staticmethod
    def _refs_for(
        relations: tuple[ClaimRelation, ...],
        relation_type: ClaimRelationType,
    ) -> tuple[RecordRef, ...]:
        return tuple(
            dict.fromkeys(
                relation.source_ref for relation in relations if relation.relation is relation_type
            )
        )

    def _aggregate_strength(
        self,
        refs: tuple[RecordRef, ...],
        claims: dict[RecordRef, ClaimRecord],
    ) -> float:
        usable = [
            self._claim_strength(claims[ref]) for ref in refs if self._claim_is_usable(claims[ref])
        ]
        return sum(usable) / len(usable) if usable else 0.0

    @staticmethod
    def _claim_strength(claim: ClaimRecord) -> float:
        validation_multiplier = {
            ValidationStatus.VERIFIED: 1.0,
            ValidationStatus.PARTIAL: 0.75,
            ValidationStatus.UNVERIFIED: 0.40,
            ValidationStatus.REJECTED: 0.0,
        }[claim.validation_status]
        return claim.confidence * validation_multiplier

    @staticmethod
    def _claim_is_usable(claim: ClaimRecord) -> bool:
        return claim.validation_status is not ValidationStatus.REJECTED and claim.confidence >= 0.5
