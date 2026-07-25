# Atlas ROS v5.6.0 Release Scope

Status: Compatibility release candidate scope; production promotion is not authorized.

Included: roadmap Wave 5 Execution Orchestration and Provider Separation; immutable
ExecutionAuthorizationV2, ExecutionCommandV2, ProviderOperation, ExecutionTransactionV2,
TransactionJournalEntry, RecoveryInstruction, and ExecutionReceiptV2 contracts; deterministic
provider-neutral command construction; exact action, scope, count, plan, digest, actor, expiry,
revocation, and replay authorization checks; bounded retries; idempotent replay; uncertain-apply
readback; partial-failure and compensation handling; fail-closed receipts; content-safe evidence;
Todoist and Notion execution adapters; W03 compatibility delegation; provider-separation and
anti-bypass architecture gates; versioned schemas; a 64-case orchestration benchmark; packaging;
and Drive-independent restoration.

Preserved: Atlas ROS v5.5.0 production behavior, V1 planning and execution compatibility paths,
W-number aliases, Task Economy constraints, exact Todoist Objective and Done When rendering,
management-domain routing, parent/subtask hierarchy, attended authorization, provider readback,
reconciliation safety, integration permissions, authority separation, and fail-closed behavior.

Excluded: unattended consequential execution, real provider writes during validation, new
integrations, permission expansion, calendar/email/messaging writes, deletion, autonomous
scheduling, W-number retirement, Active-manifest cutover, final release publication, rollback
change, and production promotion.

Promotion requires exact-artifact Full Validation and Ryan's explicit authorization.
