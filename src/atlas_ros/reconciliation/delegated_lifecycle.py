"""Fail-closed delegated lifecycle readback and partial-failure assessment."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from atlas_ros.contracts.digests import sha256_digest
from atlas_ros.contracts.operational_awareness import TodoistLifecyclePlanV1


@dataclass(frozen=True, slots=True)
class DelegatedLifecycleReconciliationAssessment:
    consistent: bool
    verified_identities: tuple[str, ...]
    missing_or_mismatched: tuple[str, ...]
    recovery_actions: tuple[str, ...]
    assessment_digest: str

    @classmethod
    def create(
        cls,
        *,
        consistent: bool,
        verified_identities: tuple[str, ...],
        missing_or_mismatched: tuple[str, ...],
        recovery_actions: tuple[str, ...],
    ) -> DelegatedLifecycleReconciliationAssessment:
        payload = {
            "consistent": consistent,
            "verified_identities": verified_identities,
            "missing_or_mismatched": missing_or_mismatched,
            "recovery_actions": recovery_actions,
        }
        return cls(
            consistent=consistent,
            verified_identities=verified_identities,
            missing_or_mismatched=missing_or_mismatched,
            recovery_actions=recovery_actions,
            assessment_digest=sha256_digest(payload),
        )


@dataclass(frozen=True, slots=True)
class DelegatedLifecycleReconciler:
    """Compare exact plan identities with provider readbacks without writing."""

    def assess(
        self,
        plan: TodoistLifecyclePlanV1,
        *,
        notion_readback: dict[str, Any] | None,
        todoist_readback: dict[str, Any] | None,
    ) -> DelegatedLifecycleReconciliationAssessment:
        notion_operation = plan.notion_operations[0]
        checkpoint_operations = tuple(
            item
            for item in plan.todoist_operations
            if item.action == "upsert_current_checkpoint"
        )
        checkpoint_operation = checkpoint_operations[-1] if checkpoint_operations else None
        natural = (
            plan.command_interpretation.command.fields.get("intent-origin")
            == "task-update"
        )
        verified: list[str] = []
        mismatched: list[str] = []
        recovery: list[str] = []
        notion_url: str | None = None

        if notion_readback is None:
            mismatched.append("notion readback missing")
            recovery.append("read back authoritative Delegated Work before any retry")
        else:
            exact_notion_match = all(
                notion_readback.get(key) == value
                for key, value in notion_operation.expected_readback.items()
            )
            notion_url_value = str(notion_readback.get("canonical_url") or "").strip()
            notion_url_valid = not natural or notion_url_value.startswith("https://")
            if exact_notion_match and notion_url_valid:
                notion_url = notion_url_value or None
                verified.append(notion_operation.idempotency_key)
            else:
                mismatched.append("notion identity, command digest, or URL mismatch")
                recovery.append("reconcile Notion from the exact authorized operation")

        if checkpoint_operation is not None:
            if todoist_readback is None:
                mismatched.append("todoist checkpoint readback missing")
                recovery.append("read back checkpoint by projection identity before any retry")
            else:
                exact_todoist_match = all(
                    todoist_readback.get(key) == value
                    for key, value in checkpoint_operation.expected_readback.items()
                )
                linked_url_matches = (
                    not natural
                    or (
                        notion_url is not None
                        and todoist_readback.get("authoritative_record_url") == notion_url
                    )
                )
                if exact_todoist_match and linked_url_matches:
                    verified.append(checkpoint_operation.idempotency_key)
                else:
                    mismatched.append(
                        "todoist checkpoint identity, due date, or Notion link mismatch"
                    )
                    recovery.append("resume the exact idempotent checkpoint operation")

        return DelegatedLifecycleReconciliationAssessment.create(
            consistent=not mismatched,
            verified_identities=tuple(verified),
            missing_or_mismatched=tuple(mismatched),
            recovery_actions=tuple(recovery),
        )
