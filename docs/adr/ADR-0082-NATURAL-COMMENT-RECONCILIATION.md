# ADR-0082: Governed Natural-Language Todoist Comment Reconciliation

- **Status:** v8.2.0 candidate; not production authority
- **Authority baseline:** Atlas ROS v8.1.0, resolved from live authority
- **Immediate rollback baseline:** Atlas ROS v8.0.0, resolved from live authority

## Context

The v8 task-update normalizer accepted task content and descriptions but ordinary Todoist comments were not connected to it. The reconciliation service retrieved comments but interpreted only explicit `@atlas` prefixes. Universal Inbox reconciliation could therefore omit a material Todoist update, and an unseen ordinary comment could be silently ignored. The connector acceptance suite also bypassed comment ingestion by invoking normalization directly.

## Decision

Use one canonical Todoist comment-source adapter and the existing typed command lifecycle. For every unprocessed comment on a governed parent task or linked subtask, reconciliation first attempts backward-compatible explicit `@atlas` parsing and otherwise invokes deterministic natural-language normalization. Every unseen event is classified and recorded as Awaiting Approval, Blocked, Informational, Ignored, Applied, or Failed.

Natural interpretation remains bounded. It supports enumerated commitment constructions, same-comment single-antecedent pronouns, Ryan-owned follow-up language, timezone-aware relative dates, and narrowly derived outcomes and completion criteria. Every material field carries origin, evidence, confidence, rationale, and ambiguity. Inferred material fields require attended authorization bound to the exact plan digest and event identities.

`Reconcile ROS` and `Reconcile ROS inbox` are composite ingress aliases covering Universal Inbox plus governed Todoist parents, subtasks, comments, execution changes, and unprocessed ledger events. Explicit Inbox-only, Todoist-only, and task-specific scopes remain isolated.

## Ledger decision

Do not add production Notion properties. Preserve the complete versioned event envelope as deterministic JSON in the existing reconciliation-state `Notes` property while retaining stable event identity and physical persistence status in existing top-level fields. Local SQLite state uses additive typed columns. This avoids writing unsupported properties or targeting a historical schema.

## Consequences

- Ordinary comments are never silently discarded.
- Event identity, not a global timestamp, is authoritative for deduplication.
- A bounded overlap watermark is retrieval optimization only.
- Interpretation and planning perform zero provider writes.
- Informational events cannot create execution intent.
- Parent outcomes remain open unless their complete Definition of Done is verified.
- At most one active Ryan-owned checkpoint remains after authorized apply.
- The feature composes with v8.1 clarification but does not use broad or unrestricted model-only classification.
- Promotion requires exact-package authorization, independent publication readback, no-migration readback, and final live authority readback.
