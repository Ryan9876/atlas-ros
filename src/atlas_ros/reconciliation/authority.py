from __future__ import annotations

from atlas_ros.contracts.reconciliation_v2 import (
    AuthoritySource,
    FieldAuthorityRegistry,
    FieldAuthorityRule,
    UpdateDirection,
)


def default_field_authority_registry() -> FieldAuthorityRegistry:
    todoist_fields = (
        ("execution_due_date", "date"),
        ("execution_priority", "priority"),
        ("parent_completed", "boolean"),
        ("subtask_completed", "boolean"),
        ("todoist_task_id", "text"),
        ("todoist_updated_at", "date"),
        ("atlas_command", "text"),
    )
    notion_fields = (
        "responsibility",
        "desired_outcome",
        "management_context",
        "strategic_rationale",
        "workstream_ownership",
        "governance",
        "approvals",
        "decision_history",
        "management_risks",
        "evidence_requirements",
        "canonical_record_id",
        "planning_content",
    )
    rules = [
        FieldAuthorityRule(
            field=name,
            authority=AuthoritySource.TODOIST,
            direction=UpdateDirection.TODOIST_TO_NOTION,
            normalization=normalization,  # type: ignore[arg-type]
        )
        for name, normalization in todoist_fields
    ]
    rules.extend(
        FieldAuthorityRule(
            field=name,
            authority=AuthoritySource.NOTION,
            direction=UpdateDirection.NOTION_TO_TODOIST,
            normalization="text",
        )
        for name in notion_fields
    )
    rules.extend(
        (
            FieldAuthorityRule(
                field="sync_state",
                authority=AuthoritySource.DERIVED,
                direction=UpdateDirection.DERIVE_ONLY,
                normalization="text",
            ),
            FieldAuthorityRule(
                field="last_verified",
                authority=AuthoritySource.DERIVED,
                direction=UpdateDirection.DERIVE_ONLY,
                normalization="date",
            ),
        )
    )
    return FieldAuthorityRegistry(policy_version="2.0.0", rules=tuple(rules))
