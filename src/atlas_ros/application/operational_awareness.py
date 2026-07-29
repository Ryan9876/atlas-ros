"""Deterministic read-only Operational Awareness coordinator."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from atlas_ros.capabilities.operational_awareness import (
    CommitmentIntelligence,
    ExecutionContextService,
    OperatingBriefService,
    OperationalSnapshotBuilder,
    WorkGraphHygieneService,
    WorkStateIntelligence,
)
from atlas_ros.contracts.digests import sha256_digest
from atlas_ros.contracts.operational_awareness import (
    AwarenessStageReceiptV1,
    CommitmentAssessmentV1,
    ExecutionContextPackV1,
    HygieneFindingV1,
    OperatingBriefV1,
    OperationalAwarenessReceiptV1,
    OperationalSnapshotV1,
    WorkStateEstimateV1,
)
from atlas_ros.policy.operational_awareness import OperationalAwarenessPolicy
from atlas_ros.ports.operational_state import OperationalStateReadPort


@dataclass(frozen=True, slots=True)
class OperationalAwarenessResult:
    snapshot: OperationalSnapshotV1
    work_states: tuple[WorkStateEstimateV1, ...]
    commitments: tuple[CommitmentAssessmentV1, ...]
    brief: OperatingBriefV1
    context_packs: tuple[ExecutionContextPackV1, ...]
    hygiene_findings: tuple[HygieneFindingV1, ...]
    receipt: OperationalAwarenessReceiptV1


@dataclass(frozen=True, slots=True)
class OperationalAwarenessCoordinator:
    """Run every awareness capability in canonical deterministic order."""

    policy: OperationalAwarenessPolicy

    def run(
        self,
        port: OperationalStateReadPort,
        *,
        scope: str,
        generated_at: datetime | None = None,
        previous: OperationalSnapshotV1 | None = None,
    ) -> OperationalAwarenessResult:
        snapshot = OperationalSnapshotBuilder(self.policy).build(
            port.read_records(scope=scope),
            scope=scope,
            authority_identities=port.authority_identities(),
            missing_sources=port.missing_sources(),
            contradictions=port.contradictions(),
            generated_at=generated_at,
        )
        states = WorkStateIntelligence(self.policy).estimate_all(
            snapshot, evaluated_at=generated_at
        )
        commitments = CommitmentIntelligence(self.policy).assess_all(
            snapshot, states, evaluated_at=generated_at
        )
        brief = OperatingBriefService(self.policy).generate(
            snapshot,
            states,
            commitments,
            previous=previous,
            generated_at=generated_at,
        )
        context_service = ExecutionContextService(self.policy)
        contexts = tuple(
            context_service.build(
                snapshot, states, record_id=record.record_ref.canonical_record_id
            )
            for record in snapshot.normalized_records
        )
        hygiene = WorkGraphHygieneService(self.policy)
        hygiene.graph(snapshot, states)
        findings = hygiene.scan(snapshot, states)
        values = (
            ("snapshot_normalization", snapshot.snapshot_digest),
            ("work_state_estimation", sha256_digest([item.estimate_digest for item in states])),
            (
                "commitment_assessment",
                sha256_digest([item.assessment_digest for item in commitments]),
            ),
            ("change_detection_and_brief", brief.brief_digest),
            ("execution_context", sha256_digest([item.context_digest for item in contexts])),
            ("work_graph_hygiene", sha256_digest([item.finding_digest for item in findings])),
        )
        receipts: list[AwarenessStageReceiptV1] = []
        input_digest = snapshot.snapshot_digest
        for stage, output_digest in values:
            receipts.append(
                AwarenessStageReceiptV1.create(
                    stage=stage,
                    input_digest=input_digest,
                    output_digest=output_digest,
                    provider_writes=0,
                )
            )
            input_digest = output_digest
        receipt = OperationalAwarenessReceiptV1.create(
            snapshot_digest=snapshot.snapshot_digest,
            policy_digest=self.policy.policy_digest,
            stage_receipts=tuple(receipts),
            provider_writes=0,
            replay_id=snapshot.replay_id,
        )
        return OperationalAwarenessResult(
            snapshot=snapshot,
            work_states=states,
            commitments=commitments,
            brief=brief,
            context_packs=contexts,
            hygiene_findings=findings,
            receipt=receipt,
        )
