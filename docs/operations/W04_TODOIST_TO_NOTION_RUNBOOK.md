# W04 Todoist-to-Notion Reconciliation

## Purpose

W04 keeps Notion reporting current by reconciling governed Todoist execution changes back to ROS. It is attended and review-first in this candidate.

## Authority

Todoist owns execution due date, execution priority, completion state, subtask completion, and explicitly prefixed `@atlas` comments. Notion retains authority for management priority, Definition of Done, accountable ownership, portfolio relationships, risk severity, and reporting structure.

## Supported commands

- `@atlas update <status>`
- `@atlas delegate <resource> by YYYY-MM-DD` followed by the delegated outcome
- `@atlas blocker <description>`
- `@atlas unblock <resolution>`
- `@atlas checkpoint YYYY-MM-DD`

Unprefixed comments are ignored.

## Transaction

1. Read mapped Action Records.
2. Read canonical Todoist parents, completed tasks, subtasks, and comments.
3. Build a dry-run plan.
4. Stop on mapping or field-authority conflicts.
5. Require explicit confirmation.
6. Write Notion changes.
7. Read back every write.
8. Record processed comment IDs and advance the checkpoint only after success.

## Failure handling

Conflicts are written to ROS Operations when configured. W04 never overwrites Notion-authoritative management fields and never treats a webhook payload as canonical state.
## Comment-command ingestion requirements (v4.4.2)

- Read comments from the governed parent task and every linked subtask.
- Process only comments beginning with `@atlas`.
- Accept `@atlas update text` and `@atlas update: text`.
- Route parent updates to the Action Record and subtask updates to the linked Execution Step.
- Parse `@atlas delegate Ryan` and `@atlas delegate to Ryan`; resolve an unambiguous Notion person into Assigned Person while retaining Assigned Resource text.
- Record Todoist comment IDs in shared reconciliation state before advancing the checkpoint.
- Preserve ordinary comments without mutation.
- Surface missing mappings, ambiguous people, and malformed commands as reviewable conflicts.

