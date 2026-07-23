from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from atlas_ros.intelligence.record_store import SQLiteIntelligenceRecordStore
from atlas_ros.intelligence.records import (
    AssumptionRecord,
    AssumptionStatus,
    ClaimRecord,
    ClaimType,
    InferenceRule,
    InferenceStep,
    InferenceTraceRecord,
    RecordKind,
    RecordRef,
    ValidationStatus,
)


@dataclass(frozen=True)
class InferenceOutcome:
    conclusion: ClaimRecord
    trace: InferenceTraceRecord


@dataclass(frozen=True)
class InferenceRequest:
    """Specification for executing a governed inference."""

    rule_ref: RecordRef
    premise_refs: tuple[RecordRef, ...]
    conclusion_statement: str
    target_options: tuple[str, ...]
    claim_type: ClaimType = ClaimType.INTERPRETATION

    def __post_init__(self) -> None:
        if not self.premise_refs:
            raise ValueError("inference requests require at least one premise")
        if not self.target_options or any(not option.strip() for option in self.target_options):
            raise ValueError("inference requests require at least one non-empty target option")
        if len(self.target_options) != len(set(self.target_options)):
            raise ValueError("inference target options must be unique")


class GovernedInferenceEngine:
    """Deterministic, auditable inference over governed claims and assumptions."""

    def __init__(self, record_store: SQLiteIntelligenceRecordStore) -> None:
        self.record_store = record_store

    def infer(
        self,
        *,
        rule_ref: RecordRef,
        premise_refs: tuple[RecordRef, ...],
        conclusion_statement: str,
        claim_type: ClaimType = ClaimType.INTERPRETATION,
        created_at: datetime | None = None,
    ) -> InferenceOutcome:
        rule = self.record_store.resolve(rule_ref)
        if not isinstance(rule, InferenceRule):
            raise ValueError("rule_ref must resolve to InferenceRule")
        if not rule.active:
            raise ValueError("inactive inference rules cannot be executed")
        if len(premise_refs) < rule.minimum_premises:
            raise ValueError(f"inference rule requires at least {rule.minimum_premises} premises")
        if len(premise_refs) != len(set(premise_refs)):
            raise ValueError("inference premise references must be unique")

        confidence_values: list[float] = []
        validation_values: list[ValidationStatus] = []
        evidence_refs: list[RecordRef] = []
        steps: list[InferenceStep] = []

        for position, premise_ref in enumerate(premise_refs, start=1):
            premise = self.record_store.resolve(premise_ref)

            if isinstance(premise, ClaimRecord):
                confidence = premise.confidence
                validation_status = premise.validation_status
                evidence_refs.extend(premise.evidence_refs)
                description = f"Applied claim premise {position}: {premise.statement}"
            elif isinstance(premise, AssumptionRecord):
                confidence = premise.confidence
                validation_status = self._assumption_validation(premise.status)
                evidence_refs.extend(premise.evidence_refs)
                description = f"Applied assumption premise {position}: {premise.assumption}"
            elif isinstance(premise, InferenceTraceRecord):
                confidence = premise.confidence
                validation_status = premise.validation_status
                conclusion = self.record_store.resolve(premise.conclusion_ref)
                if not isinstance(conclusion, ClaimRecord):
                    raise ValueError("inference trace conclusion_ref must resolve to ClaimRecord")
                evidence_refs.extend(conclusion.evidence_refs)
                description = f"Applied prior inference premise {position}: {conclusion.statement}"
            else:
                raise ValueError(
                    "inference premises must resolve to ClaimRecord, "
                    "AssumptionRecord, or InferenceTraceRecord"
                )

            confidence_values.append(confidence)
            validation_values.append(validation_status)
            steps.append(
                InferenceStep(
                    sequence=position,
                    premise_ref=premise_ref,
                    description=description,
                    confidence=confidence,
                    validation_status=validation_status,
                )
            )

        unique_evidence_refs = tuple(dict.fromkeys(evidence_refs))
        if not unique_evidence_refs:
            raise ValueError("inference requires evidence-backed premises")

        validation_status = self._combined_validation(validation_values)
        premise_confidence = min(confidence_values)
        confidence = max(
            0.0,
            min(
                1.0,
                premise_confidence
                * rule.reliability
                * self._validation_multiplier(validation_status),
            ),
        )

        conclusion = ClaimRecord(
            created_at=created_at or datetime.now(UTC),
            statement=conclusion_statement,
            claim_type=claim_type,
            confidence=confidence,
            validation_status=validation_status,
            evidence_refs=unique_evidence_refs,
            links=tuple(dict.fromkeys((rule_ref, *premise_refs))),
        )

        trace = InferenceTraceRecord(
            created_at=created_at or conclusion.created_at,
            rule_ref=rule_ref,
            premise_refs=premise_refs,
            conclusion_ref=conclusion.ref(),
            steps=tuple(steps),
            confidence=confidence,
            validation_status=validation_status,
            valid=validation_status is not ValidationStatus.REJECTED,
            explanation=(
                f"Applied inference rule '{rule.name}' to {len(premise_refs)} governed premises."
            ),
            links=tuple(dict.fromkeys((rule_ref, *premise_refs, conclusion.ref()))),
        )

        return InferenceOutcome(
            conclusion=conclusion,
            trace=trace,
        )

    @staticmethod
    def _assumption_validation(
        status: AssumptionStatus,
    ) -> ValidationStatus:
        return {
            AssumptionStatus.VERIFIED: ValidationStatus.VERIFIED,
            AssumptionStatus.PARTIAL: ValidationStatus.PARTIAL,
            AssumptionStatus.UNVERIFIED: ValidationStatus.UNVERIFIED,
            AssumptionStatus.REJECTED: ValidationStatus.REJECTED,
        }[status]

    @staticmethod
    def _combined_validation(
        statuses: list[ValidationStatus],
    ) -> ValidationStatus:
        rank = {
            ValidationStatus.VERIFIED: 3,
            ValidationStatus.PARTIAL: 2,
            ValidationStatus.UNVERIFIED: 1,
            ValidationStatus.REJECTED: 0,
        }
        return min(statuses, key=rank.__getitem__)

    @staticmethod
    def _validation_multiplier(
        status: ValidationStatus,
    ) -> float:
        return {
            ValidationStatus.VERIFIED: 1.0,
            ValidationStatus.PARTIAL: 0.80,
            ValidationStatus.UNVERIFIED: 0.50,
            ValidationStatus.REJECTED: 0.0,
        }[status]


def valid_inference_premise_kind(kind: RecordKind) -> bool:
    return kind in {
        RecordKind.CLAIM,
        RecordKind.ASSUMPTION,
        RecordKind.INFERENCE_TRACE,
    }
