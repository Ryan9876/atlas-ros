"""Typed command interpretation and lifecycle-plan compilation."""

from __future__ import annotations

from dataclasses import dataclass

from atlas_ros.contracts.advisory_v1 import ConfidenceAssessment
from atlas_ros.contracts.digests import sha256_digest
from atlas_ros.contracts.operational_awareness import (
    AtlasCommandType,
    AtlasCommandV1,
    CommandInterpretationV1,
    EffectiveWorkState,
    NextActionProjectionV1,
    NormalizedOperationalRecordV1,
    OperationalSnapshotV1,
    ProviderOperationSpecV1,
    TodoistLifecyclePlanV1,
)
from atlas_ros.policy.operational_awareness import OperationalAwarenessPolicy


class LifecyclePlanningError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class CommandLifecycleService:
    policy: OperationalAwarenessPolicy

    def interpret(
        self,
        command: AtlasCommandV1,
        snapshot: OperationalSnapshotV1,
    ) -> CommandInterpretationV1:
        records = {
            item.record_ref.canonical_record_id: item for item in snapshot.normalized_records
        }
        source_record = self._resolve_source_record(command, snapshot)
        parent = self._resolve_parent(command, source_record, records)
        ambiguity: list[str] = []
        blockers: list[str] = []
        if parent is None:
            ambiguity.append("parent outcome could not be resolved uniquely")
            blockers.append("resolve the exact persistent parent outcome")
        responsible = command.subject or command.fields.get("responsible")
        if command.command_type == AtlasCommandType.DELEGATE and not responsible:
            ambiguity.append("delegation requires a responsible party")
            blockers.append("resolve the assignee identity")
        expected_outcome = command.fields.get("outcome") or command.fields.get("expected")
        if command.command_type == AtlasCommandType.DELEGATE and not expected_outcome:
            ambiguity.append("delegation requires an expected outcome")
            blockers.append("provide the delegated outcome")
        done_when = command.fields.get("done-when")
        completion_criteria = (done_when,) if done_when else source_record.definition_of_done
        if command.command_type == AtlasCommandType.DELEGATE and not completion_criteria:
            ambiguity.append("delegation requires completion criteria")
            blockers.append("provide done-when criteria")
        checkpoint = command.fields.get("follow-up") or command.fields.get("checkpoint")
        if checkpoint is None and self.policy.command.missing_checkpoint_behavior == "reject":
            blockers.append("checkpoint is required by policy")
        next_action = self._next_action(command, responsible, expected_outcome)
        score = 1.0 if not ambiguity else max(0.0, 1.0 - 0.3 * len(ambiguity))
        return CommandInterpretationV1.create(
            command=command,
            parent_outcome=parent.record_ref if parent is not None else None,
            affected_notion_record=source_record.record_ref,
            responsible_party=responsible,
            accountable_party=source_record.accountable_party or source_record.owner or "Ryan",
            expected_outcome=(
                expected_outcome or source_record.expected_outcome or source_record.title
            ),
            completion_criteria=completion_criteria,
            next_checkpoint=checkpoint,
            next_ryan_owned_action=next_action,
            confidence=ConfidenceAssessment(
                score=score,
                rationale=(
                    "explicit command normalized deterministically"
                    if not ambiguity
                    else "command is blocked by unresolved deterministic ambiguity"
                ),
            ),
            ambiguity=tuple(ambiguity),
            blockers=tuple(blockers),
        )

    def plan(
        self,
        interpretation: CommandInterpretationV1,
        snapshot: OperationalSnapshotV1,
    ) -> TodoistLifecyclePlanV1:
        if interpretation.blockers or interpretation.parent_outcome is None:
            raise LifecyclePlanningError(
                "blocked command interpretation cannot create a lifecycle plan"
            )
        command = interpretation.command
        records = {
            item.record_ref.canonical_record_id: item for item in snapshot.normalized_records
        }
        parent = records[interpretation.parent_outcome.canonical_record_id]
        active_checkpoints = tuple(
            str(item) for item in parent.extra.get("active_ryan_checkpoint_ids", ())
        )
        action_title = interpretation.next_ryan_owned_action
        state = self._resulting_state(command.command_type)
        notion_payload = {
            "record_id": interpretation.affected_notion_record.canonical_record_id
            if interpretation.affected_notion_record
            else parent.record_ref.canonical_record_id,
            "transition": command.command_type.value,
            "responsible_party": interpretation.responsible_party,
            "accountable_party": interpretation.accountable_party,
            "expected_outcome": interpretation.expected_outcome,
            "completion_criteria": interpretation.completion_criteria,
            "checkpoint": interpretation.next_checkpoint,
            "effective_state": state.value,
            "command_digest": command.command_digest,
        }
        notion_operation = ProviderOperationSpecV1.create(
            provider="notion",
            action="upsert_management_state",
            target=notion_payload["record_id"],
            payload=notion_payload,
            idempotency_key=f"{command.idempotency_identity}:notion",
            expected_readback={
                "transition": command.command_type.value,
                "effective_state": state.value,
                "command_digest": command.command_digest,
            },
        )
        todoist_operations: list[ProviderOperationSpecV1] = []
        for task_id in active_checkpoints:
            todoist_operations.append(
                ProviderOperationSpecV1.create(
                    provider="todoist",
                    action="complete_obsolete_checkpoint",
                    target=task_id,
                    payload={"task_id": task_id, "reason": "successor lifecycle transition"},
                    idempotency_key=f"{command.idempotency_identity}:close:{task_id}",
                    expected_readback={"completed": True},
                )
            )
        if action_title:
            next_identity = sha256_digest(
                {
                    "parent": parent.todoist_task_id,
                    "title": action_title,
                    "checkpoint": interpretation.next_checkpoint,
                }
            )
            todoist_operations.append(
                ProviderOperationSpecV1.create(
                    provider="todoist",
                    action="upsert_current_checkpoint",
                    target=parent.todoist_task_id or parent.record_ref.canonical_record_id,
                    payload={
                        "parent_task_id": parent.todoist_task_id,
                        "content": action_title,
                        "due": interpretation.next_checkpoint,
                        "projection_identity": next_identity,
                    },
                    idempotency_key=f"{command.idempotency_identity}:checkpoint:{next_identity}",
                    expected_readback={
                        "parent_task_id": parent.todoist_task_id,
                        "content": action_title,
                        "due": interpretation.next_checkpoint,
                    },
                )
            )
        parent_close_allowed = (
            command.command_type == AtlasCommandType.COMPLETE and self._parent_done(parent)
        )
        if parent_close_allowed and parent.todoist_task_id:
            todoist_operations.append(
                ProviderOperationSpecV1.create(
                    provider="todoist",
                    action="complete_parent_after_definition_of_done",
                    target=parent.todoist_task_id,
                    payload={"task_id": parent.todoist_task_id, "verified_done": True},
                    idempotency_key=f"{command.idempotency_identity}:parent-complete",
                    expected_readback={"completed": True},
                )
            )
        projection = NextActionProjectionV1.create(
            parent_outcome=parent.record_ref,
            action_title=action_title,
            due_date_or_checkpoint=interpretation.next_checkpoint,
            reason=f"typed {command.command_type.value} lifecycle transition",
            replaces_task_ids=active_checkpoints,
            preserves_parent=True,
            active_checkpoint_count_after=1 if action_title else 0,
        )
        operations = (notion_operation, *todoist_operations)
        if len(operations) > self.policy.command.max_object_count:
            raise LifecyclePlanningError("command plan exceeds compiled object budget")
        return TodoistLifecyclePlanV1.create(
            command_interpretation=interpretation,
            parent_outcome=parent.record_ref,
            notion_operations=(notion_operation,),
            todoist_operations=tuple(todoist_operations),
            next_action_projection=projection,
            maximum_object_count=self.policy.command.max_object_count,
            authorization_scope=(
                f"exact command {command.command_digest}; parent "
                f"{parent.record_ref.canonical_record_id}; {len(operations)} operation(s)"
            ),
            expected_readback=tuple(
                f"{operation.provider}:{operation.target}:{operation.operation_digest}"
                for operation in operations
            ),
            compensation_behavior=(
                "resume idempotently from the transaction journal; restore prior provider values "
                "when the canonical transaction requires compensation"
            ),
            blockers=(),
        )

    @staticmethod
    def _resolve_source_record(
        command: AtlasCommandV1,
        snapshot: OperationalSnapshotV1,
    ) -> NormalizedOperationalRecordV1:
        candidates = [
            record
            for record in snapshot.normalized_records
            if record.todoist_task_id == command.source.source_task_id
            or record.record_ref.canonical_record_id == command.source.source_task_id
        ]
        if len(candidates) != 1:
            raise LifecyclePlanningError("source command task does not resolve uniquely")
        return candidates[0]

    @staticmethod
    def _resolve_parent(
        command: AtlasCommandV1,
        source_record: NormalizedOperationalRecordV1,
        records: dict[str, NormalizedOperationalRecordV1],
    ) -> NormalizedOperationalRecordV1 | None:
        candidate_ids = {
            item
            for item in (
                command.source.parent_task_id,
                source_record.record_ref.parent_record_id,
                source_record.extra.get("parent_record_id"),
            )
            if isinstance(item, str) and item
        }
        candidates = [
            record
            for record in records.values()
            if record.record_ref.canonical_record_id in candidate_ids
            or record.todoist_task_id in candidate_ids
        ]
        if source_record.record_ref.record_type.value == "action_record" and not candidates:
            return source_record
        return candidates[0] if len(candidates) == 1 else None

    @staticmethod
    def _next_action(
        command: AtlasCommandV1,
        responsible: str | None,
        expected_outcome: str | None,
    ) -> str | None:
        outcome = expected_outcome or command.subject or "the outcome"
        mapping = {
            AtlasCommandType.DELEGATE: (
                f"Follow up with {responsible} on {outcome}" if responsible else None
            ),
            AtlasCommandType.UPDATE: None,
            AtlasCommandType.WAITING_ON: f"Follow up on {command.subject or outcome}",
            AtlasCommandType.BLOCKED: (
                f"Resolve {command.subject or outcome}"
                if command.fields.get("ryan-owns") == "true"
                else None
            ),
            AtlasCommandType.RECEIVED: f"Review {command.subject or outcome}",
            AtlasCommandType.APPROVED: command.fields.get("next-action"),
            AtlasCommandType.COMPLETE: None,
            AtlasCommandType.CANCEL: command.fields.get("next-action"),
        }
        return mapping[command.command_type]

    @staticmethod
    def _resulting_state(command_type: AtlasCommandType) -> EffectiveWorkState:
        return {
            AtlasCommandType.DELEGATE: EffectiveWorkState.DELEGATED,
            AtlasCommandType.UPDATE: EffectiveWorkState.ACTIVE,
            AtlasCommandType.WAITING_ON: EffectiveWorkState.WAITING,
            AtlasCommandType.BLOCKED: EffectiveWorkState.BLOCKED,
            AtlasCommandType.RECEIVED: EffectiveWorkState.REVIEW,
            AtlasCommandType.APPROVED: EffectiveWorkState.ACTIVE,
            AtlasCommandType.COMPLETE: EffectiveWorkState.AWAITING_VALIDATION,
            AtlasCommandType.CANCEL: EffectiveWorkState.CANCELLED,
        }[command_type]

    @staticmethod
    def _parent_done(parent: NormalizedOperationalRecordV1) -> bool:
        return bool(
            parent.definition_of_done
            and parent.completion_evidence
            and not parent.extra.get("open_child_ids")
            and (not parent.approval_required or parent.approval_received)
        )
