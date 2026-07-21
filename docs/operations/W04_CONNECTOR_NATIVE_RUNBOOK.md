# W04 Connector-Native Todoist-to-Notion Reconciliation

## Purpose

Allow Atlas in ChatGPT to execute the same attended, review-first W04 transaction as the local CLI while sharing replay state with CLI executions.

## Invocation

- `Atlas, reconcile Todoist.` — full mapped-task dry run.
- `Atlas, reconcile <task name or Todoist task ID>.` — scoped dry run.
- `Atlas, apply the reconciliation.` — apply only the previously presented plan.

## Transaction

1. Read the active Release Index, System State, active manifest, and Integration Inventory.
2. Read mapped Action Records where Execution System is Todoist and Execution Object ID is present.
3. Read canonical Todoist parents, completed tasks, subtasks, and comments.
4. Read the shared Reconciliation State ledger and suppress applied comment IDs.
5. Build and present a dry-run plan containing mutations, ignored items, and conflicts.
6. Require Ryan's explicit approval before applying.
7. Write only Todoist-authoritative execution fields and structured `@atlas` outcomes.
8. Read back every Notion write.
9. Record applied comment IDs and advance the shared checkpoint only after all writes verify.
10. Re-run the same scope to prove zero-mutation replay idempotency.

## Shared ledger schema

Data source: `W04 Reconciliation State`

- State Key (title; unique logical key)
- State Type (Checkpoint, Processed Event)
- Status (Applied, Failed)
- Cursor (date/time)
- Event ID (text)
- Processed At (date/time)
- Execution Surface (CLI, ChatGPT)
- Notes (text)

The CLI uses this ledger when `ATLAS_RECONCILIATION_STATE_DATA_SOURCE_ID` is configured. Without it, v4.4 retains the local SQLite fallback for recovery only.

## Authority

Todoist owns execution due date, execution priority, completion state, subtask completion, and explicitly prefixed `@atlas` comments. Notion retains management priority, Definition of Done, accountable ownership, portfolio relationships, risk severity, and reporting structure.

## Safety

No unattended apply, autonomous scheduling, messaging, email, calendar action, or deletion is activated.
## Comment-command ingestion requirements (v4.4.2)

- Read comments from the governed parent task and every linked subtask.
- Process only comments beginning with `@atlas`.
- Accept `@atlas update text` and `@atlas update: text`.
- Route parent updates to the Action Record and subtask updates to the linked Execution Step.
- Parse `@atlas delegate Ryan` and `@atlas delegate to Ryan`; resolve an unambiguous Notion person into Assigned Person while retaining Assigned Resource text.
- Record Todoist comment IDs in shared reconciliation state before advancing the checkpoint.
- Preserve ordinary comments without mutation.
- Surface missing mappings, ambiguous people, and malformed commands as reviewable conflicts.

