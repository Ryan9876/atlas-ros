from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from atlas_ros.intelligence.reasoning import OptionAssessment
from atlas_ros.intelligence.records import (
    AuthorityLevel,
    ContextSnapshot,
    EvidenceEnvelope,
    RecordRef,
    ValidationStatus,
)

_AUTHORITY_SCORES: dict[AuthorityLevel, float] = {
    AuthorityLevel.PRIMARY: 1.00,
    AuthorityLevel.AUTHORITATIVE_APPLICATION: 0.95,
    AuthorityLevel.GOVERNED_INTERNAL: 0.85,
    AuthorityLevel.USER_PROVIDED: 0.75,
    AuthorityLevel.INFERRED: 0.45,
    AuthorityLevel.UNVERIFIED: 0.20,
}

_VALIDATION_SCORES: dict[ValidationStatus, float] = {
    ValidationStatus.VERIFIED: 1.00,
    ValidationStatus.PARTIAL: 0.72,
    ValidationStatus.UNVERIFIED: 0.35,
    ValidationStatus.REJECTED: 0.00,
}


@dataclass(frozen=True)
class BenchmarkScoringSignals:
    authority_strength: float
    validation_strength: float
    confidence_strength: float
    corroboration: float
    provenance_quality: float
    freshness: float
    context_completeness: float
    constraint_clarity: float
    rejected_evidence_ratio: float

    @property
    def evidence_support(self) -> float:
        return _bounded(
            0.30 * self.confidence_strength
            + 0.25 * self.validation_strength
            + 0.20 * self.authority_strength
            + 0.15 * self.corroboration
            + 0.10 * self.provenance_quality
        )

    @property
    def governance_fit(self) -> float:
        return _bounded(
            0.45 * self.authority_strength
            + 0.30 * self.validation_strength
            + 0.15 * self.context_completeness
            + 0.10 * self.constraint_clarity
        )

    @property
    def actionability(self) -> float:
        return _bounded(
            0.40 * self.context_completeness
            + 0.25 * self.constraint_clarity
            + 0.20 * self.evidence_support
            + 0.15 * self.freshness
        )

    @property
    def unsupported_risk(self) -> float:
        support = (
            0.40 * self.evidence_support
            + 0.25 * self.governance_fit
            + 0.20 * self.actionability
            + 0.15 * self.freshness
        )
        return _bounded(1.0 - support + 0.35 * self.rejected_evidence_ratio)


class BenchmarkScoringEngine:
    """Derives reasoning-option scores from evidence and context signals."""

    def analyze(
        self,
        evidence: tuple[EvidenceEnvelope, ...],
        context: ContextSnapshot,
        *,
        evaluated_at: datetime,
    ) -> BenchmarkScoringSignals:
        if not evidence:
            return BenchmarkScoringSignals(
                authority_strength=0.0,
                validation_strength=0.0,
                confidence_strength=0.0,
                corroboration=0.0,
                provenance_quality=0.0,
                freshness=0.0,
                context_completeness=self._context_completeness(context),
                constraint_clarity=self._constraint_clarity(context),
                rejected_evidence_ratio=1.0,
            )

        non_rejected = tuple(
            item for item in evidence if item.validation_status is not ValidationStatus.REJECTED
        )

        authority_strength = self._average(
            tuple(_AUTHORITY_SCORES[item.source_authority] for item in non_rejected)
        )
        validation_strength = self._average(
            tuple(_VALIDATION_SCORES[item.validation_status] for item in evidence)
        )
        confidence_strength = self._average(tuple(item.confidence for item in non_rejected))
        corroboration = min(1.0, len(non_rejected) / 3.0)
        provenance_quality = self._average(
            tuple(self._provenance_quality(item) for item in evidence)
        )
        freshness = self._average(
            tuple(self._freshness(item, evaluated_at) for item in non_rejected)
        )
        rejected_ratio = sum(
            item.validation_status is ValidationStatus.REJECTED for item in evidence
        ) / len(evidence)

        return BenchmarkScoringSignals(
            authority_strength=authority_strength,
            validation_strength=validation_strength,
            confidence_strength=confidence_strength,
            corroboration=corroboration,
            provenance_quality=provenance_quality,
            freshness=freshness,
            context_completeness=self._context_completeness(context),
            constraint_clarity=self._constraint_clarity(context),
            rejected_evidence_ratio=rejected_ratio,
        )

    def build_options(
        self,
        *,
        governed_label: str,
        evidence_refs: tuple[RecordRef, ...],
        signals: BenchmarkScoringSignals,
    ) -> tuple[OptionAssessment, ...]:
        governance_fit = signals.governance_fit
        evidence_support = signals.evidence_support
        actionability = signals.actionability
        unsupported_risk = signals.unsupported_risk

        return (
            OptionAssessment(
                option=governed_label,
                scores={
                    "governance_fit": governance_fit,
                    "evidence_support": evidence_support,
                    "actionability": actionability,
                    "unsupported_risk": unsupported_risk,
                },
                expected_benefit=(
                    f"Apply the governed {governed_label} behavior using "
                    "the available authority and evidence."
                ),
                expected_risk=(
                    "Acting on incomplete, weak, stale, or insufficiently "
                    "validated evidence could produce an unsupported result."
                ),
                evidence_refs=evidence_refs,
            ),
            OptionAssessment(
                option="abstain",
                scores={
                    "governance_fit": 1.0 - governance_fit,
                    "evidence_support": 1.0 - evidence_support,
                    "actionability": 1.0 - actionability,
                    "unsupported_risk": 1.0 - unsupported_risk,
                },
                expected_benefit=(
                    "Avoid issuing an unsupported recommendation until "
                    "stronger evidence or authority is available."
                ),
                expected_risk=(
                    "A warranted governed action may be delayed despite "
                    "adequate supporting evidence."
                ),
                evidence_refs=evidence_refs,
            ),
        )

    @staticmethod
    def _average(values: tuple[float, ...]) -> float:
        return sum(values) / len(values) if values else 0.0

    @staticmethod
    def _provenance_quality(evidence: EvidenceEnvelope) -> float:
        indicators = (
            bool(evidence.source_locator),
            bool(evidence.source_content_hash),
            bool(evidence.citation),
            bool(evidence.provenance),
        )
        return sum(indicators) / len(indicators)

    @staticmethod
    def _freshness(
        evidence: EvidenceEnvelope,
        evaluated_at: datetime,
    ) -> float:
        age_seconds = max(
            0.0,
            (evaluated_at - evidence.observed_at).total_seconds(),
        )
        age_days = age_seconds / 86_400
        return _bounded(1.0 - age_days / 365.0)

    @staticmethod
    def _context_completeness(context: ContextSnapshot) -> float:
        indicators = (
            bool(context.active_objective),
            bool(context.decision_horizon),
            bool(context.environment),
            bool(context.available_authorities),
            bool(context.evidence_refs),
            bool(context.session_lineage),
        )
        return sum(indicators) / len(indicators)

    @staticmethod
    def _constraint_clarity(context: ContextSnapshot) -> float:
        if context.constraints:
            return min(1.0, 0.65 + 0.10 * len(context.constraints))
        return 0.55


def _bounded(value: float) -> float:
    return max(0.0, min(1.0, value))
