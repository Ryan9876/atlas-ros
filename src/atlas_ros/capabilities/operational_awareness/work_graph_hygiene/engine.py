"""Self-maintaining work-graph analysis and governed repair proposals."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass

from atlas_ros.contracts.advisory_v1 import ConfidenceAssessment
from atlas_ros.contracts.digests import sha256_digest
from atlas_ros.contracts.operational_awareness import (
    EffectiveWorkState,
    HygieneFindingV1,
    HygieneSeverity,
    NormalizedOperationalRecordV1,
    OperationalRecordRefV1,
    OperationalSnapshotV1,
    RepairClass,
    RepairProposalV1,
    WorkGraphEdgeV1,
    WorkGraphNodeV1,
    WorkGraphSnapshotV1,
    WorkStateEstimateV1,
)
from atlas_ros.policy.operational_awareness import OperationalAwarenessPolicy


@dataclass(frozen=True, slots=True)
class WorkGraphHygieneService:
    policy: OperationalAwarenessPolicy

    def graph(
        self,
        snapshot: OperationalSnapshotV1,
        estimates: tuple[WorkStateEstimateV1, ...],
    ) -> WorkGraphSnapshotV1:
        state_by_id = {
            item.record_reference.canonical_record_id: item.effective_state
            for item in estimates
        }
        nodes = tuple(
            WorkGraphNodeV1.create(
                record_reference=record.record_ref,
                effective_state=state_by_id[record.record_ref.canonical_record_id].value,
                protected_history=record.protected_history,
            )
            for record in snapshot.normalized_records
        )
        edges: list[WorkGraphEdgeV1] = []
        for record in snapshot.normalized_records:
            source_id = record.record_ref.canonical_record_id
            if record.record_ref.parent_record_id:
                edges.append(
                    WorkGraphEdgeV1.create(
                        source_record_id=record.record_ref.parent_record_id,
                        target_record_id=source_id,
                        edge_type="parent-child",
                    )
                )
            for dependency in record.dependencies:
                edges.append(
                    WorkGraphEdgeV1.create(
                        source_record_id=dependency,
                        target_record_id=source_id,
                        edge_type="dependency",
                    )
                )
            for blocker in record.blockers:
                edges.append(
                    WorkGraphEdgeV1.create(
                        source_record_id=blocker,
                        target_record_id=source_id,
                        edge_type="blocking",
                    )
                )
            if record.todoist_task_id:
                edges.append(
                    WorkGraphEdgeV1.create(
                        source_record_id=source_id,
                        target_record_id=record.todoist_task_id,
                        edge_type="provider-representation",
                    )
                )
        ordered_edges = tuple(
            sorted(
                edges,
                key=lambda item: (
                    item.source_record_id,
                    item.target_record_id,
                    item.edge_type,
                ),
            )
        )
        return WorkGraphSnapshotV1.create(
            snapshot_id=f"work-graph:{snapshot.snapshot_id}",
            nodes=nodes,
            edges=ordered_edges,
        )

    def scan(
        self,
        snapshot: OperationalSnapshotV1,
        estimates: tuple[WorkStateEstimateV1, ...],
    ) -> tuple[HygieneFindingV1, ...]:
        records = list(snapshot.normalized_records)
        by_id = {item.record_ref.canonical_record_id: item for item in records}
        state_by_id = {
            item.record_reference.canonical_record_id: item.effective_state
            for item in estimates
        }
        findings: list[HygieneFindingV1] = []

        title_counts = Counter(
            (item.record_ref.record_type.value, item.title.strip().lower())
            for item in records
        )
        todoist_counts = Counter(item.todoist_task_id for item in records if item.todoist_task_id)
        children_by_parent: dict[str, list[NormalizedOperationalRecordV1]] = defaultdict(list)
        for record in records:
            if record.record_ref.parent_record_id:
                children_by_parent[record.record_ref.parent_record_id].append(record)

        for record in records:
            record_id = record.record_ref.canonical_record_id
            protected = record.protected_history or record.record_ref.record_type.value in set(
                self.policy.hygiene.protected_record_types
            )
            eligibility = RepairClass.PROTECTED if protected else RepairClass.INDIVIDUAL
            common = {
                "affected_records": (record.record_ref,),
                "confidence": ConfidenceAssessment(
                    score=1.0, rationale="deterministic invariant evaluation"
                ),
                "protected_record_status": protected,
            }
            key = (record.record_ref.record_type.value, record.title.strip().lower())
            if title_counts[key] > 1 and record.record_ref.record_type.value in {
                "action_record",
                "execution_step",
            }:
                findings.append(
                    self._finding(
                        record_id,
                        "duplicate-record",
                        evidence=(f"duplicate title/type key: {key}",),
                        severity=HygieneSeverity.HIGH,
                        downstream=(
                            "duplicate work representations can create conflicting execution intent"
                        ),
                        disposition="review and consolidate exact duplicates",
                        eligibility=eligibility,
                        **common,
                    )
                )
            if record.todoist_task_id and todoist_counts[record.todoist_task_id] > 1:
                findings.append(
                    self._finding(
                        record_id,
                        "duplicate-todoist-representation",
                        evidence=(
                            f"Todoist task {record.todoist_task_id} is mapped more than once",
                        ),
                        severity=HygieneSeverity.HIGH,
                        downstream="provider representation is ambiguous",
                        disposition="retain one canonical mapping after attended review",
                        eligibility=eligibility,
                        **common,
                    )
                )
            parent_id = record.record_ref.parent_record_id
            if parent_id and parent_id not in by_id:
                findings.append(
                    self._finding(
                        record_id,
                        "orphaned-child",
                        evidence=(f"missing parent {parent_id}",),
                        severity=HygieneSeverity.HIGH,
                        downstream="work cannot be traced to a persistent outcome",
                        disposition="restore the exact parent relationship",
                        eligibility=eligibility,
                        **common,
                    )
                )
            if record.completed and any(
                not child.completed and not child.cancelled
                for child in children_by_parent.get(record_id, [])
            ):
                findings.append(
                    self._finding(
                        record_id,
                        "completed-parent-open-child",
                        evidence=("parent completed while child work remains open",),
                        severity=HygieneSeverity.CRITICAL,
                        downstream="persistent outcome may have been closed prematurely",
                        disposition="reopen parent or validate child disposition",
                        eligibility=eligibility,
                        **common,
                    )
                )
            if record.cancelled and any(
                not child.completed and not child.cancelled
                for child in children_by_parent.get(record_id, [])
            ):
                findings.append(
                    self._finding(
                        record_id,
                        "cancelled-parent-active-child",
                        evidence=("cancelled parent retains active child work",),
                        severity=HygieneSeverity.HIGH,
                        downstream="active work is no longer attached to a valid outcome",
                        disposition="cancel, supersede, or reparent active children",
                        eligibility=eligibility,
                        **common,
                    )
                )
            if record.observed_state == "blocked" and not record.blockers:
                findings.append(
                    self._finding(
                        record_id,
                        "blocked-without-blocker",
                        evidence=("blocked state has no named blocker",),
                        severity=HygieneSeverity.WARNING,
                        downstream="resolution ownership and next action are unclear",
                        disposition="name and link the blocker",
                        eligibility=eligibility,
                        **common,
                    )
                )
            if record.delegated and not record.responsible_party:
                findings.append(
                    self._finding(
                        record_id,
                        "delegated-without-responsible-party",
                        evidence=("delegated outcome has no responsible party",),
                        severity=HygieneSeverity.HIGH,
                        downstream="delegation cannot be verified or followed up",
                        disposition="resolve the responsible party",
                        eligibility=RepairClass.RYAN_DECISION if not protected else eligibility,
                        **common,
                    )
                )
            if state_by_id.get(record_id) in {
                EffectiveWorkState.READY,
                EffectiveWorkState.ACTIVE,
            } and not record.definition_of_done:
                findings.append(
                    self._finding(
                        record_id,
                        "executable-without-definition-of-done",
                        evidence=("executable work lacks Definition of Done",),
                        severity=HygieneSeverity.HIGH,
                        downstream="safe completion cannot be determined",
                        disposition="define completion criteria before execution",
                        eligibility=eligibility,
                        **common,
                    )
                )
            active_checkpoints = int(record.extra.get("active_ryan_checkpoint_count", 0) or 0)
            if (
                record.delegated
                and active_checkpoints
                > self.policy.hygiene.max_active_delegated_checkpoints
            ):
                findings.append(
                    self._finding(
                        record_id,
                        "multiple-active-delegated-checkpoints",
                        evidence=(f"{active_checkpoints} active Ryan checkpoints",),
                        severity=HygieneSeverity.HIGH,
                        downstream="Todoist displays duplicate or competing next actions",
                        disposition="retain one current Ryan-owned checkpoint",
                        eligibility=eligibility,
                        **common,
                    )
                )
            if record.received_evidence and record.extra.get("obsolete_follow_up_active"):
                findings.append(
                    self._finding(
                        record_id,
                        "obsolete-follow-up-after-receipt",
                        evidence=("result received while follow-up remains active",),
                        severity=HygieneSeverity.WARNING,
                        downstream="Ryan sees an obsolete action instead of the review action",
                        disposition="close follow-up and project the review action",
                        eligibility=eligibility,
                        **common,
                    )
                )
        # Deduplicate exact rule/record pairs.
        unique = {item.finding_id: item for item in findings}
        return tuple(unique[key] for key in sorted(unique))

    def propose(
        self,
        finding: HygieneFindingV1,
    ) -> RepairProposalV1:
        if finding.repair_eligibility in {RepairClass.PROTECTED, RepairClass.NONE}:
            raise PermissionError("finding is protected or not repair-eligible")
        operations = tuple(
            {
                "provider": record.authoritative_system.value,
                "target": record.canonical_record_id,
                "action": "propose_update",
            }
            for record in finding.affected_records
        )
        identity = sha256_digest(
            {
                "finding": finding.finding_digest,
                "records": [record.source_digest for record in finding.affected_records],
            }
        )
        return RepairProposalV1.create(
            finding_id=finding.finding_id,
            exact_affected_records=finding.affected_records,
            intended_final_state=finding.proposed_disposition,
            reason=finding.downstream_impact,
            preconditions=(
                "read exact current provider revisions",
                "obtain immutable attended authorization for exact operations",
            ),
            expected_provider_operations=operations,
            reversibility="restore prior values from mandatory pre-write snapshot",
            risk_classification=finding.severity.value,
            readback_requirements=(
                "read every changed provider object",
                "verify intended final state and transaction receipt",
            ),
            idempotency_identity=f"repair:{identity}",
        )

    @staticmethod
    def _finding(
        record_id: str,
        rule_id: str,
        *,
        affected_records: tuple[OperationalRecordRefV1, ...],
        evidence: tuple[str, ...],
        severity: HygieneSeverity,
        confidence: ConfidenceAssessment,
        downstream: str,
        disposition: str,
        eligibility: RepairClass,
        protected_record_status: bool,
    ) -> HygieneFindingV1:
        return HygieneFindingV1.create(
            finding_id=f"hygiene:{rule_id}:{record_id}",
            rule_id=rule_id,
            affected_records=affected_records,
            evidence=evidence,
            severity=severity,
            confidence=confidence,
            downstream_impact=downstream,
            proposed_disposition=disposition,
            repair_eligibility=eligibility,
            protected_record_status=protected_record_status,
        )
