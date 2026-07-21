# Changelog

## 4.5.0 - 2026-07-21

- Standardize Todoist Work sections as Leadership & Team, Active Projects, Operations, Waiting on Others, and Development & Learning.
- Define Waiting on Others as a temporary dependency state that returns to Operations or Active Projects when cleared.
- Add optional Execution Priority to Execution Steps; blank inherits the parent Action priority and explicit values override it.
- Add Execution State values Ready, In Progress, Waiting, Blocked, Delegated, Review, and Complete.
- Extend W04 commands with risk, dependency, and issue routing to the production Risks and Blockers database.
- Link governed risk records to both the parent Action and applicable Execution Step using Todoist comment ID idempotency.
- Preserve attended, review-first boundaries and designate v4.4.2 as the immediate immutable rollback.

## 4.4.2 - 2026-07-21

- Fixed W04 comment ingestion to read governed parent tasks and all linked subtasks.
- Added support for colon-form commands such as `@atlas update: text`.
- Fixed `@atlas delegate to <name>` parsing and Notion person resolution.
- Delegation commands now populate Assigned Person, Assigned Resource, Resource Type, parent Action linkage, and parent Todoist task linkage.
- Subtask update comments now write to the linked Execution Step rather than overwriting the parent Action update.
- Added regression tests for parent/subtask comments, delegation assignment, linkage, and idempotent replay.

## 4.4.1 - 2026-07-21

- Promote connector-native attended W04 reconciliation after cross-surface production acceptance.
- Share processed-event and checkpoint state between ChatGPT and the macOS CLI through Notion.
- Suppress replay for comments at or before the authoritative shared checkpoint.
- Verify target macOS CLI replay produced zero mutations, ignored records, or conflicts.
- Preserve v4.3.0 as the immediate immutable rollback baseline.

## 4.3.0 - 2026-07-21

- Promote W04 Todoist-to-Notion reconciliation after controlled production acceptance.
- Verified 28 planned changes applied and read back successfully: 9 Action Record updates and 19 Execution Step creations.
- Verified immediate full replay produced zero mutations, conflicts, ignored records, or writes.
- Preserve attended, review-first operating boundaries and v4.2.0 as the immediate immutable rollback.

## 4.2.0-rc.1

- First inactive Python candidate platform, preserving v4.1.0 production and v4.0.1 rollback unchanged.
