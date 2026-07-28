# Governed Historical Cleanup Operator Runbook

## Preflight

- Obtain an immutable item-level inventory with exact locations, digests, size, release family, dependencies, and retention classification.
- Resolve every uncertain or conflicting item through a human decision.
- Prove no active or rollback release depends on any destructive target.
- Generate a dry-run plan and validate source/destination identities, object and byte budgets, and restoration evidence.

## Authorization

Destructive execution requires separate exact authorization identifying transaction ID, inventory digest, plan digest, exact item IDs, allowed actions, object budget, byte budget, and explicit destructive authority.

## Execution

Apply only exact authorized operations. Use deterministic idempotency keys, bounded retries, uncertain-apply readback, item-level failure capture, and post-operation reconciliation. Stop when source digest changes, authorization mismatches, budgets would be exceeded, or readback cannot verify state.

## Completion

A transaction is complete only when every operation and readback is represented in a digest-bound receipt. Partial results remain partial and require a new exact decision. Deletion is disabled in the candidate because no live provider adapter is enabled.
