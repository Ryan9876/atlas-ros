# ADR-014 — Atlas ROS v7.3 Command-Driven Work Lifecycle

Status: Candidate. No live command execution is authorized.

## Decision

Treat an explicit `@atlas` command as bounded lifecycle intent, not execution authorization. Normalize the command into immutable typed contracts, resolve one persistent parent outcome, project at most one active Ryan-owned checkpoint, and submit exact operations to the existing canonical planning and attended-execution boundary.

## Invariants

1. The parent Todoist outcome is preserved until verified Definition of Done.
2. Delegated implementation is represented in Notion, not as Ryan-owned Todoist execution.
3. Replays use the same command and operation identities and cannot create duplicates.
4. Obsolete checkpoints close before a successor is created; completed history remains.
5. Missing or ambiguous parent, assignee, outcome, or completion criteria fails closed.
6. Exact authorization binds command text, source revision, targets, operation budget, idempotency, readback, and compensation.
7. Coordinators and adapters cannot authorize themselves.

## Supported commands

`delegate`, `update`, `waiting-on`, `blocked`, `received`, `approved`, `complete`, and `cancel`.
