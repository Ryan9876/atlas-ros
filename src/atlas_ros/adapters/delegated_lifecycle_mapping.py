"""Pure provider payload mapping for delegated lifecycle operations.

These functions translate exact plans only. They do not resolve permissions,
authorize execution, or invoke Notion or Todoist.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from atlas_ros.contracts.operational_awareness import ProviderOperationSpecV1


class DelegatedLifecycleMappingError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class DelegatedLifecycleProviderMapper:
    """Map lifecycle operation payloads to provider-facing field identities."""

    @staticmethod
    def notion_properties(operation: ProviderOperationSpecV1) -> dict[str, Any]:
        if operation.provider != "notion" or operation.action != "upsert_delegated_work":
            raise DelegatedLifecycleMappingError(
                "Notion delegated mapping requires upsert_delegated_work"
            )
        payload = operation.payload
        required = (
            "record_id",
            "delegate",
            "accountable_owner",
            "expected_outcome",
            "completion_criteria",
            "delegated_date",
            "effective_state",
            "parent_action_record",
            "source_update",
            "command_digest",
            "idempotency_identity",
            "latest_reconciliation_state",
        )
        missing = tuple(key for key in required if not payload.get(key))
        if missing:
            raise DelegatedLifecycleMappingError(
                f"delegated work payload missing: {', '.join(missing)}"
            )
        properties: dict[str, Any] = {
            "Delegated Outcome": payload["expected_outcome"],
            "Assigned Resource": payload["delegate"],
            "Assigned Person": payload["delegate"],
            "Accountable Owner": payload["accountable_owner"],
            "Done When": "\n".join(payload["completion_criteria"]),
            "date:Assigned Date:start": payload["delegated_date"],
            "date:Assigned Date:is_datetime": 1,
            "Acceptance Status": "Unconfirmed",
            "Effective State": payload["effective_state"],
            "Parent Action": [payload["parent_action_record"]],
            "Source Update": payload["source_update"],
            "Provenance": payload.get("provenance", []),
            "Command Digest": payload["command_digest"],
            "Idempotency Identity": payload["idempotency_identity"],
            "Latest Reconciliation State": payload["latest_reconciliation_state"],
        }
        if payload.get("delegate_due"):
            properties["date:Delivery Due Date:start"] = payload["delegate_due"]
            properties["date:Delivery Due Date:is_datetime"] = 0
        if payload.get("follow_up_checkpoint"):
            properties["date:Next Checkpoint:start"] = payload["follow_up_checkpoint"]
            properties["date:Next Checkpoint:is_datetime"] = 0
        return properties

    @staticmethod
    def todoist_checkpoint(operation: ProviderOperationSpecV1) -> dict[str, Any]:
        if operation.provider != "todoist" or operation.action != "upsert_current_checkpoint":
            raise DelegatedLifecycleMappingError(
                "Todoist checkpoint mapping requires upsert_current_checkpoint"
            )
        payload = operation.payload
        content = str(payload.get("content") or "").strip()
        authoritative_identity = str(
            payload.get("authoritative_record_identity") or ""
        ).strip()
        description = str(payload.get("description") or "").strip()
        if not content or " on " not in content:
            raise DelegatedLifecycleMappingError(
                "Todoist delegated checkpoint must name the followed outcome"
            )
        if not authoritative_identity or authoritative_identity not in description:
            raise DelegatedLifecycleMappingError(
                "Todoist checkpoint must link to the authoritative Notion identity"
            )
        return {
            "parent_id": payload.get("parent_task_id"),
            "content": content,
            "description": description,
            "due": payload.get("due"),
            "projection_identity": payload.get("projection_identity"),
            "authoritative_record_identity": authoritative_identity,
        }
