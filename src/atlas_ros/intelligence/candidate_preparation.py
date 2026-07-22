from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Mapping, Sequence

from pydantic import BaseModel, ConfigDict, Field, model_validator

from atlas_ros.intelligence.release_readiness import (
    GateStatus,
    ReadinessAssessment,
    ReadinessDecision,
)


class ReviewDisposition(StrEnum):
    APPROVED = "approved"
    CHANGES_REQUIRED = "changes_required"
    NOT_COMPLETED = "not_completed"


class PreparationDecision(StrEnum):
    BLOCKED = "blocked"
    DEVELOPMENT_COMPLETE = "development_complete"
    PROPOSABLE_CANDIDATE = "proposable_candidate"


class ArtifactDigest(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str = Field(min_length=1)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    size_bytes: int = Field(ge=0)


class ValidationExecution(BaseModel):
    model_config = ConfigDict(frozen=True)

    gate: str = Field(min_length=1)
    status: GateStatus
    command: str = Field(min_length=1)
    evidence: tuple[str, ...] = ()
    blocking: bool = True


class IndependentReview(BaseModel):
    model_config = ConfigDict(frozen=True)

    reviewer: str = Field(min_length=1)
    reviewed_at: datetime
    disposition: ReviewDisposition
    findings: tuple[str, ...] = ()
    evidence_reference: str = Field(min_length=1)

    @model_validator(mode="after")
    def require_findings_for_changes(self) -> IndependentReview:
        if self.disposition is ReviewDisposition.CHANGES_REQUIRED and not self.findings:
            raise ValueError("changes-required review must include findings")
        return self


class CandidatePreparationPolicy(BaseModel):
    model_config = ConfigDict(frozen=True)

    required_gates: frozenset[str] = frozenset(
        {
            "ruff",
            "mypy_strict",
            "tests",
            "coverage",
            "source_build",
            "wheel_build",
            "clean_wheel",
            "dependency_security",
            "benchmark_corpus",
            "adversarial_corpus",
            "regression_baseline",
            "independent_review",
            "artifact_integrity",
        }
    )
    minimum_approved_reviews: int = Field(default=1, ge=1)
    require_candidate_ready_assessment: bool = True


class CandidateEvidencePacket(BaseModel):
    model_config = ConfigDict(frozen=True)

    release_id: str = Field(min_length=1)
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    readiness_decision: ReadinessDecision
    dataset_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    executions: tuple[ValidationExecution, ...]
    reviews: tuple[IndependentReview, ...]
    artifacts: tuple[ArtifactDigest, ...]
    limitations: tuple[str, ...] = ()

    @model_validator(mode="after")
    def unique_names(self) -> CandidateEvidencePacket:
        gate_names = [item.gate for item in self.executions]
        artifact_names = [item.name for item in self.artifacts]
        if len(gate_names) != len(set(gate_names)):
            raise ValueError("validation gate names must be unique")
        if len(artifact_names) != len(set(artifact_names)):
            raise ValueError("artifact names must be unique")
        return self

    @property
    def fingerprint(self) -> str:
        payload = self.model_dump(mode="json", exclude={"generated_at"})
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha256(encoded).hexdigest()


class CandidatePreparationReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    decision: PreparationDecision
    blocking_reasons: tuple[str, ...]
    missing_gates: tuple[str, ...]
    failed_gates: tuple[str, ...]
    packet: CandidateEvidencePacket
    promotion_authorized: bool = False


class CandidatePreparationEngine:
    """Synthesizes release-candidate evidence without granting promotion authority."""

    def __init__(self, policy: CandidatePreparationPolicy | None = None) -> None:
        self.policy = policy or CandidatePreparationPolicy()

    @staticmethod
    def digest_file(path: Path) -> ArtifactDigest:
        data = path.read_bytes()
        return ArtifactDigest(
            name=path.name,
            sha256=hashlib.sha256(data).hexdigest(),
            size_bytes=len(data),
        )

    @staticmethod
    def verify_artifacts(
        artifacts: Sequence[ArtifactDigest], expected: Mapping[str, str]
    ) -> tuple[str, ...]:
        actual = {artifact.name: artifact.sha256 for artifact in artifacts}
        problems: list[str] = []
        for name, digest in sorted(expected.items()):
            if name not in actual:
                problems.append(f"missing artifact {name}")
            elif actual[name] != digest:
                problems.append(f"checksum mismatch for {name}")
        return tuple(problems)

    def prepare(
        self,
        *,
        release_id: str,
        readiness: ReadinessAssessment,
        executions: Sequence[ValidationExecution],
        reviews: Sequence[IndependentReview],
        artifacts: Sequence[ArtifactDigest],
        limitations: Sequence[str] = (),
    ) -> CandidatePreparationReport:
        execution_by_name = {item.gate: item for item in executions}
        missing = tuple(sorted(self.policy.required_gates - execution_by_name.keys()))
        failed = tuple(
            sorted(
                item.gate
                for item in executions
                if item.gate in self.policy.required_gates
                and item.blocking
                and item.status is not GateStatus.PASS
            )
        )
        approved_reviews = sum(
            review.disposition is ReviewDisposition.APPROVED for review in reviews
        )
        blocking: list[str] = []
        if missing:
            blocking.extend(f"required gate missing: {name}" for name in missing)
        if failed:
            blocking.extend(f"required gate not passed: {name}" for name in failed)
        if approved_reviews < self.policy.minimum_approved_reviews:
            blocking.append(
                f"approved independent reviews {approved_reviews}/{self.policy.minimum_approved_reviews}"
            )
        if any(
            review.disposition is ReviewDisposition.CHANGES_REQUIRED for review in reviews
        ):
            blocking.append("independent review requires changes")
        if (
            self.policy.require_candidate_ready_assessment
            and readiness.decision is not ReadinessDecision.CANDIDATE_READY
        ):
            blocking.append(f"readiness decision is {readiness.decision.value}")

        packet = CandidateEvidencePacket(
            release_id=release_id,
            readiness_decision=readiness.decision,
            dataset_fingerprint=readiness.evidence.dataset_fingerprint,
            executions=tuple(executions),
            reviews=tuple(reviews),
            artifacts=tuple(artifacts),
            limitations=tuple(limitations),
        )
        if blocking:
            decision = PreparationDecision.BLOCKED
        elif readiness.decision is ReadinessDecision.CANDIDATE_READY:
            decision = PreparationDecision.PROPOSABLE_CANDIDATE
        else:
            decision = PreparationDecision.DEVELOPMENT_COMPLETE
        return CandidatePreparationReport(
            decision=decision,
            blocking_reasons=tuple(blocking),
            missing_gates=missing,
            failed_gates=failed,
            packet=packet,
            promotion_authorized=False,
        )
