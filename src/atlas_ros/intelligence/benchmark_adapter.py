from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from atlas_ros.intelligence.benchmark_scoring import BenchmarkScoringEngine
from atlas_ros.intelligence.calibration import CalibrationCase, IntelligenceDomain
from atlas_ros.intelligence.reasoning import (
    CriterionDirection,
    DecisionCriterion,
    ReasoningRequest,
)
from atlas_ros.intelligence.record_store import SQLiteIntelligenceRecordStore
from atlas_ros.intelligence.records import (
    AuthorityLevel,
    ContextSnapshot,
    EvidenceEnvelope,
    ValidationStatus,
)

DOMAIN_LABELS: dict[IntelligenceDomain, str] = {
    IntelligenceDomain.PRIORITY: "prioritize",
    IntelligenceDomain.RISK: "escalate",
    IntelligenceDomain.DECISION: "recommend",
    IntelligenceDomain.ROOT_CAUSE: "investigate",
    IntelligenceDomain.ACTION: "act",
    IntelligenceDomain.EVIDENCE: "cite",
    IntelligenceDomain.EXPLANATION: "explain",
    IntelligenceDomain.LEARNING: "retain",
}


@dataclass(frozen=True)
class CompiledBenchmarkCase:
    case: CalibrationCase
    store: SQLiteIntelligenceRecordStore
    request: ReasoningRequest
    evidence_refs: tuple[str, ...]
    permitted_labels: frozenset[str]


class BenchmarkScenarioCompiler:
    """Compiles calibration cases into governed reasoning requests."""

    def __init__(
        self,
        database_directory: Path,
        scoring_engine: BenchmarkScoringEngine | None = None,
    ) -> None:
        self.database_directory = database_directory
        self.scoring_engine = scoring_engine or BenchmarkScoringEngine()

    def compile(self, case: CalibrationCase) -> CompiledBenchmarkCase:
        store = SQLiteIntelligenceRecordStore(
            self.database_directory / f"{self._safe_id(case.id)}.db"
        )
        store.initialize()

        created_at = datetime.now(UTC)
        evidence = self._build_evidence(case, created_at)
        context = ContextSnapshot(
            created_at=created_at,
            active_objective=case.title,
            constraints=tuple(sorted(case.tags)),
            environment={
                "benchmark_case_id": case.id,
                "intelligence_domain": case.domain.value,
            },
            available_authorities=tuple(case.authority_refs),
            decision_horizon="current benchmark evaluation",
            session_lineage=(case.id,),
            evidence_refs=tuple(item.ref() for item in evidence),
        )

        store.append_many((*evidence, context))

        governed_label = DOMAIN_LABELS[case.domain]
        signals = self.scoring_engine.analyze(
            evidence,
            context,
            evaluated_at=created_at,
        )
        evidence_record_refs = tuple(item.ref() for item in evidence)

        request = ReasoningRequest(
            objective=case.scenario,
            context_ref=context.ref(),
            criteria=self._criteria(),
            options=self.scoring_engine.build_options(
                governed_label=governed_label,
                evidence_refs=evidence_record_refs,
                signals=signals,
            ),
            minimum_evidence_confidence=0.5,
            minimum_recommendation_margin=0.05,
        )

        return CompiledBenchmarkCase(
            case=case,
            store=store,
            request=request,
            evidence_refs=tuple(case.authority_refs),
            permitted_labels=frozenset({governed_label, "abstain"}),
        )

    @staticmethod
    def _criteria() -> tuple[DecisionCriterion, ...]:
        return (
            DecisionCriterion(name="governance_fit", weight=3.0),
            DecisionCriterion(name="evidence_support", weight=2.0),
            DecisionCriterion(name="actionability", weight=2.0),
            DecisionCriterion(
                name="unsupported_risk",
                weight=2.0,
                direction=CriterionDirection.MINIMIZE,
            ),
        )

    @classmethod
    def _build_evidence(
        cls,
        case: CalibrationCase,
        created_at: datetime,
    ) -> tuple[EvidenceEnvelope, ...]:
        records: list[EvidenceEnvelope] = [
            EvidenceEnvelope(
                created_at=created_at,
                statement=case.scenario,
                source_authority=AuthorityLevel.USER_PROVIDED,
                confidence=0.82,
                observed_at=created_at,
                validation_status=ValidationStatus.PARTIAL,
                source_locator=f"benchmark:{case.id}:scenario",
                source_content_hash=cls._content_hash(case.scenario),
                citation=f"benchmark case {case.id}",
            )
        ]

        for authority_ref in case.authority_refs:
            authority, validation, confidence = cls._classify_authority(authority_ref)
            records.append(
                EvidenceEnvelope(
                    created_at=created_at,
                    statement=(
                        f"Authority reference available for benchmark case "
                        f"{case.id}: {authority_ref}"
                    ),
                    source_authority=authority,
                    confidence=confidence,
                    observed_at=created_at,
                    validation_status=validation,
                    source_locator=authority_ref,
                    source_content_hash=cls._content_hash(authority_ref),
                    citation=authority_ref,
                )
            )

        return tuple(records)

    @staticmethod
    def _classify_authority(
        authority_ref: str,
    ) -> tuple[AuthorityLevel, ValidationStatus, float]:
        normalized = authority_ref.casefold()

        primary_tokens = (
            "release index",
            "manifest",
            "policy",
            "contract",
            "authoritative",
            "source of truth",
        )
        application_tokens = (
            "notion",
            "google drive",
            "todoist",
            "system state",
            "inventory",
            "register",
        )
        weak_tokens = (
            "memory",
            "chat history",
            "assumption",
            "inference",
            "unverified",
        )

        if any(token in normalized for token in primary_tokens):
            return AuthorityLevel.PRIMARY, ValidationStatus.VERIFIED, 0.96
        if any(token in normalized for token in application_tokens):
            return (
                AuthorityLevel.AUTHORITATIVE_APPLICATION,
                ValidationStatus.VERIFIED,
                0.93,
            )
        if any(token in normalized for token in weak_tokens):
            return AuthorityLevel.INFERRED, ValidationStatus.PARTIAL, 0.60
        return (
            AuthorityLevel.GOVERNED_INTERNAL,
            ValidationStatus.PARTIAL,
            0.84,
        )

    @staticmethod
    def _content_hash(value: str) -> str:
        digest = hashlib.sha256(value.encode("utf-8")).hexdigest()
        return f"sha256:{digest}"

    @staticmethod
    def _safe_id(case_id: str) -> str:
        return "".join(
            character if character.isalnum() or character in "-_" else "_" for character in case_id
        )
