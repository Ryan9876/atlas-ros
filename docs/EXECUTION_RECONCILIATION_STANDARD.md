# Execution Reconciliation Standard

## Ownership

The canonical service plans from immutable provider snapshots, applies a versioned field-authority
registry, emits deterministic mutations and conflicts, and advances an integrity-protected
checkpoint only after complete provider readback.

## Authority

- Todoist: execution dates, execution priority, completion, task identity/timestamps, governed
  execution commands.
- Notion: responsibility, outcomes, management context, rationale, ownership, governance,
  approvals, decision history, management risks, evidence, canonical identity, planning content.
- Derived: synchronization state and verification metadata.

Unknown or ambiguous fields fail closed. Undocumented bidirectional merge is prohibited.

## Transaction invariant

Planning never writes or advances state. Application requires attended authorization for the exact
plan digest and ordered mutations. A conflict, exception, permission failure, stale checkpoint, or
readback mismatch preserves the prior checkpoint. Partially applied idempotency keys survive for
read-before-retry. A receipt is consistent only when every required mutation is applied or proven
already applied, every readback matches, no blocking conflict exists, and the checkpoint is
verified.

## Commands

Supported commands are update, delegate, risk, blocker, dependency, issue, unblock, and checkpoint.
Content-bearing commands fail closed when empty. Checkpoint values must be ISO dates. Stable
provider event identity is part of every command idempotency key.

## Safety

Reconciliation cannot create unplanned execution work, determine task existence, reinterpret an
execution plan, expand provider permissions, authorize itself, or perform unattended writes.
