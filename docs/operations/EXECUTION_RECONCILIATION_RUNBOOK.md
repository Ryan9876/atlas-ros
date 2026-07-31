# Execution Reconciliation

## Purpose

Execution Reconciliation keeps Notion management state aligned with governed Todoist execution state. It is attended, review-first, and read-before-write.

## Current production boundary

Under Active Atlas ROS v8.1.0, Todoist owns execution due date, execution priority, completion state, and subtask completion. Explicit governed comments remain supported:

- `@atlas update <status>`
- `@atlas delegate <resource> by YYYY-MM-DD` followed by the delegated outcome
- `@atlas blocker <description>`
- `@atlas unblock <resolution>`
- `@atlas checkpoint YYYY-MM-DD`

Unprefixed comments do not create production transitions under v8.1.0.

## v8.2.0 candidate behavior

After exact-package promotion and activation, every unseen comment on a governed parent or linked subtask is a stable source event. Reconciliation first parses explicit `@atlas` commands and otherwise runs bounded deterministic natural-language interpretation. Events are reported as Awaiting Approval, Blocked, Informational, Ignored, Applied, or Failed. Informational events cannot create execution intent.

## Command scopes

- `Reconcile ROS` — composite Universal Inbox and Todoist ingress dry run.
- `Reconcile ROS inbox` — same composite ingress dry run.
- `Reconcile Universal Inbox only` — Universal Inbox only.
- `Reconcile Todoist only` — all mapped Todoist parents, subtasks, comments, execution changes, and unprocessed ledger events.
- `Reconcile <task name or task ID>` — one uniquely resolved governed Todoist parent and its linked subtasks/comments.

Every run reports exact sources and object counts.

## Transaction

1. Resolve live authority and required integrations.
2. Read authoritative source records and provider state.
3. Retrieve governed parents, linked subtasks, and their comments using a bounded overlap window.
4. Suppress only terminal events with matching stable event identities.
5. Interpret explicit commands or bounded natural language.
6. Present all mutations, provider operations, inferred fields, provenance, blockers, ignored reasons, conflicts, and the plan digest.
7. Require exact attended authorization for every actionable natural-language event and the exact plan digest.
8. Execute only authorized operations.
9. Read back every write by stable identity.
10. Record each event in shared reconciliation state.
11. Advance the checkpoint only after verified completion.
12. Replay the same scope and verify zero duplicate writes.

## Shared ledger

The existing Notion reconciliation-state schema remains unchanged. Stable identity and persistence status use existing top-level properties. A versioned JSON event envelope in `Notes` preserves event type, provider, task/comment identity, posted timestamp, digest, classification, logical state, confidence, blockers, command/plan digests, authorization identity, outcome, and execution surface. Local SQLite uses additive typed columns.

## Failure handling

Fail closed on authority, mapping, person resolution, pronoun, date meaning, expected outcome, completion test, authorization, provider, or readback uncertainty. Preserve the prior checkpoint on partial or uncertain application. Reconcile by exact identities before retrying a write that might already have succeeded.
