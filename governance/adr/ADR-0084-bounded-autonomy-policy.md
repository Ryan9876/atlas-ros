# ADR-0084: Bounded-autonomy policy

Status: Accepted for the v8.3.0 candidate; production policy inactive.

## Decision

Every event plan is evaluated by a versioned policy returning exactly `AUTO_APPLY`, `REQUIRE_ATTENDED_APPROVAL`, or `BLOCK`. The provider event is evidence and a trigger, never authorization. The policy evaluates live authority agreement, source and destination, Ryan ownership, canonical mapping, field authority, exact mutations, inference, reversibility, readback, causal depth, conflicts, and limits.

The initial candidate policy is `8.3.0-rc1`, `MONITOR_ONLY`, kill switch enabled. Automatic application cannot occur until exact production policy activation after promotion.

## Matrix

| Decision | Initial scope |
|---|---|
| Auto-apply after activation | Todoist execution due date, priority, completion/reopen, mapped subtask state, deterministic non-consequential updates, reconciliation evidence, and eligible Ryan-owned Universal Inbox task creation |
| Attended approval | Delegation, material inference, unproven parent closure, free-text governance records, shared/cross-project work, non-approved destinations, mutation-limit breaches, tombstones, and corrective writes after partial failure |
| Block | Authority disagreement, W04 identity, ambiguous mapping, field-authority violation, deletion/cascade, credentials, permission or integration-scope change, messaging/email/calendar/live-network action, release activation, invalid signature/integrity, or self-authorization |

Approvals bind the exact event set, provider snapshot digests, plan digest, authority version, policy version, and expiry. Changed preconditions invalidate approval.

## Invariants

- Planning performs zero provider writes and never advances a checkpoint.
- Adapters translate typed mutations; they do not plan or authorize.
- Every mutation is read-before-write, idempotent, read back, and receipted.
- Partial application preserves the prior checkpoint and records the truthful result.
- The kill switch disables new automatic applications without stopping evidence intake.
