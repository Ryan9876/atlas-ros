# Atlas ROS v5.6.0rc1 Release Notes

This release candidate completes Execution Orchestration and Provider Separation. Validated
Execution Plan V2 objects can be transformed into deterministic, provider-neutral execution
commands only when an exact, unexpired, unrevoked, one-time authorization covers the same plan,
digest, actor, action, provider, operation scope, and object count.

The orchestrator owns transaction state, bounded retry, idempotency, uncertain-apply readback,
partial-failure handling, recovery instructions, compensation decisions, chained journal
evidence, and fail-closed receipts. Provider adapters own mapping, transport, immediate readback,
and safe error classification; they cannot plan, authorize, or manufacture success.

The Todoist adapter preserves exact Objective and Done When rendering, section routing, and
parent/subtask hierarchy. The Notion adapter uses explicit writable mappings, detects schema
drift and ambiguous identity matches, and verifies writes by readback. W03 delegates through the
new orchestration boundary while its compatibility surface remains available.

The candidate benchmark contains 64 orchestration cases, including all critical authorization,
replay, timeout, retry, duplicate, schema-drift, partial-failure, compensation, receipt, and
provider-separation scenarios. Validation performs no live provider writes and grants no
unattended authority. Rollback is Atlas ROS v5.5.0; no external data migration is performed.
