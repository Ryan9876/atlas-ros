from datetime import UTC, datetime
from pathlib import Path

import pytest

from atlas_ros.intelligence.candidate_preparation import (
    ArtifactDigest,
    CandidatePreparationEngine,
    IndependentReview,
    PreparationDecision,
    ReviewDisposition,
    ValidationExecution,
)
from atlas_ros.intelligence.release_readiness import (
    EvidenceGate,
    GateStatus,
    ReadinessAssessment,
    ReadinessDecision,
    ReleaseEvidence,
)


def readiness(decision: ReadinessDecision = ReadinessDecision.CANDIDATE_READY) -> ReadinessAssessment:
    evidence = ReleaseEvidence(
        release_id="v5.0",
        dataset_fingerprint="a" * 64,
        benchmark_score=0.95,
        regression_passed=True,
        adversarial_passed=True,
        gates=(EvidenceGate(name="tests", status=GateStatus.PASS),),
    )
    return ReadinessAssessment(decision=decision, blocking_reasons=(), evidence=evidence)


def executions(status: GateStatus = GateStatus.PASS) -> tuple[ValidationExecution, ...]:
    return tuple(
        ValidationExecution(gate=name, status=status, command=f"run {name}")
        for name in sorted(CandidatePreparationEngine().policy.required_gates)
    )


def review(disposition: ReviewDisposition = ReviewDisposition.APPROVED) -> IndependentReview:
    return IndependentReview(
        reviewer="independent-reviewer",
        reviewed_at=datetime.now(UTC),
        disposition=disposition,
        findings=("fix required",) if disposition is ReviewDisposition.CHANGES_REQUIRED else (),
        evidence_reference="review-1",
    )


def test_digest_file_is_deterministic(tmp_path: Path) -> None:
    path = tmp_path / "artifact.txt"
    path.write_text("atlas")
    first = CandidatePreparationEngine.digest_file(path)
    second = CandidatePreparationEngine.digest_file(path)
    assert first == second
    assert first.size_bytes == 5


def test_verify_artifacts_detects_missing_and_mismatch() -> None:
    artifacts = (ArtifactDigest(name="a", sha256="a" * 64, size_bytes=1),)
    problems = CandidatePreparationEngine.verify_artifacts(
        artifacts, {"a": "b" * 64, "b": "c" * 64}
    )
    assert problems == ("checksum mismatch for a", "missing artifact b")


def test_changes_required_review_requires_findings() -> None:
    with pytest.raises(ValueError, match="must include findings"):
        IndependentReview(
            reviewer="r",
            reviewed_at=datetime.now(UTC),
            disposition=ReviewDisposition.CHANGES_REQUIRED,
            evidence_reference="review",
        )


def test_missing_gate_blocks_candidate() -> None:
    result = CandidatePreparationEngine().prepare(
        release_id="v5.0",
        readiness=readiness(),
        executions=executions()[:-1],
        reviews=(review(),),
        artifacts=(),
    )
    assert result.decision is PreparationDecision.BLOCKED
    assert result.missing_gates
    assert not result.promotion_authorized


def test_failed_gate_blocks_candidate() -> None:
    items = list(executions())
    items[0] = items[0].model_copy(update={"status": GateStatus.FAIL})
    result = CandidatePreparationEngine().prepare(
        release_id="v5.0",
        readiness=readiness(),
        executions=items,
        reviews=(review(),),
        artifacts=(),
    )
    assert result.decision is PreparationDecision.BLOCKED
    assert result.failed_gates == (items[0].gate,)


def test_changes_required_review_blocks_candidate() -> None:
    result = CandidatePreparationEngine().prepare(
        release_id="v5.0",
        readiness=readiness(),
        executions=executions(),
        reviews=(review(ReviewDisposition.CHANGES_REQUIRED),),
        artifacts=(),
    )
    assert result.decision is PreparationDecision.BLOCKED
    assert "independent review requires changes" in result.blocking_reasons


def test_non_candidate_readiness_blocks_candidate() -> None:
    result = CandidatePreparationEngine().prepare(
        release_id="v5.0",
        readiness=readiness(ReadinessDecision.DEVELOPMENT_VALIDATED),
        executions=executions(),
        reviews=(review(),),
        artifacts=(),
    )
    assert result.decision is PreparationDecision.BLOCKED
    assert "readiness decision is development_validated" in result.blocking_reasons


def test_complete_evidence_is_proposable_not_promoted() -> None:
    result = CandidatePreparationEngine().prepare(
        release_id="v5.0",
        readiness=readiness(),
        executions=executions(),
        reviews=(review(),),
        artifacts=(ArtifactDigest(name="package.zip", sha256="f" * 64, size_bytes=10),),
    )
    assert result.decision is PreparationDecision.PROPOSABLE_CANDIDATE
    assert not result.blocking_reasons
    assert not result.promotion_authorized
    assert len(result.packet.fingerprint) == 64


def test_packet_rejects_duplicate_gate_names() -> None:
    duplicate = executions()[:1] * 2
    with pytest.raises(ValueError, match="gate names must be unique"):
        CandidatePreparationEngine().prepare(
            release_id="v5.0",
            readiness=readiness(),
            executions=duplicate,
            reviews=(review(),),
            artifacts=(),
        )
