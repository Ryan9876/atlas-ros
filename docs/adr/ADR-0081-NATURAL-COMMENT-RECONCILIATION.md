# ADR-0081: Governed Natural-Language Todoist Comment Reconciliation

- **Status:** Candidate; not production authority
- **Authority baseline:** Resolve from live `governance/AUTHORITY.json`

## Context

The Active v8 task-update normalizer accepted task content and descriptions but was not connected to ordinary Todoist comments. The existing reconciliation service read comments but interpreted only `@atlas` prefixes. A Universal Inbox-only operation could therefore omit a material Todoist update, and a newly discovered ordinary comment could be silently classified as ignored.

## Decision

Use one canonical comment-source adapter and the existing typed command lifecycle. For every unprocessed parent-task or subtask comment, reconciliation first attempts explicit `@atlas` parsing and otherwise invokes deterministic natural-language normalization. It records every event as actionable, blocked, informational, ignored, applied, or failed.

Natural interpretation remains bounded. It supports explicit commitment constructions, same-comment single-antecedent pronouns, Ryan-owned follow-up language, timezone-aware date resolution, and narrowly derived outcomes and completion criteria. Material inference is displayed and requires authorization bound to the exact plan digest and event IDs.

`Reconcile ROS` and `Reconcile ROS inbox` are composite planning aliases. They inspect Universal Inbox and Todoist ingress while preserving separate authority and write paths. Scoped Inbox-only, Todoist-only, and task-specific modes remain available.

## Consequences

- Ordinary comments are never silently discarded.
- Event identity, not a global timestamp, is authoritative for deduplication.
- The global watermark is a bounded retrieval optimization only.
- Provider writes remain zero during interpretation and planning.
- Parent outcomes remain open unless their complete Definition of Done is verified.
- One active Ryan-owned checkpoint is preserved by completing the obsolete checkpoint before upserting its successor.
- The shared ledger needs an additive, rollback-compatible schema extension.
- Promotion requires exact-package authorization, migration readback, independent publication readback, and final live authority readback.
