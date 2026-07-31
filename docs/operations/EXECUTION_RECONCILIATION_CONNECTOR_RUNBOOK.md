# Connector-Native Execution Reconciliation

## Purpose

Allow Atlas in ChatGPT to perform the same attended, review-first reconciliation transaction as the CLI while sharing replay state and provider boundaries.

## Invocation

- `Reconcile ROS` or `Reconcile ROS inbox` — composite ingress dry run.
- `Reconcile Universal Inbox only` — scoped Inbox dry run.
- `Reconcile Todoist only` — scoped Todoist dry run.
- `Reconcile <task name or Todoist task ID>` — scoped governed-task dry run.
- `Apply the reconciliation` — apply only the exact previously presented plan after exact attended authorization.

## Transaction

1. Read live authority in the required order.
2. Read mapped Action Records and current Universal Inbox records for the selected scope.
3. Read governed Todoist parents, linked subtasks, task state, and comments.
4. Read the shared reconciliation ledger and use stable event identity as the authoritative deduplication key.
5. Parse explicit `@atlas` commands first; otherwise use the bounded v8.2 natural-comment lifecycle.
6. Present source counters, new event IDs, classifications, inferred field origins, confidence, blockers, ignored reasons, conflicts, mutations, provider operations, and plan digest.
7. Require Ryan's exact attended approval covering the plan digest and actionable event IDs.
8. Execute only the authorized provider operations and read back each write.
9. Record every event outcome and advance the checkpoint only after verified completion.
10. Replay the same scope and prove zero duplicates.

## Shared ledger schema

Data source: configured Execution Reconciliation State source.

Existing top-level properties:

- State Key
- State Type
- Status
- Cursor
- Event ID
- Processed At
- Execution Surface
- Notes

No v8.2 production Notion property additions are required. The complete versioned event envelope is JSON in `Notes`. The physical Status remains Applied/Failed; the envelope carries the logical reconciliation state.

## Authority

Todoist owns execution due date, execution priority, completion state, and subtask completion. Comments are immutable source evidence. Notion remains authoritative for management priority, Definition of Done, accountable ownership, portfolio relationships, risk severity, and reporting structure.

## Safety

Interpretation does not authorize planning; planning does not authorize execution. Adapters cannot create execution intent. No unattended apply, autonomous scheduling, messaging, email, calendar action, deletion, credential action, or integration-scope expansion is enabled.
