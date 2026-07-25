# ADR-009 — Canonical Reconciliation and Numbered-Workflow Retirement

Status: Accepted for the unpromoted Atlas ROS v6.0.0 candidate.

## Decision

Atlas ROS v6 uses semantic capabilities as the sole runtime architecture. The canonical flow is:

Capture Envelope → Reasoning Package → Knowledge Package → Management Package → Execution Plan →
Execution Receipt → Reconciliation Plan → Reconciliation Receipt.

The Execution Reconciliation Service owns field authority, command meaning, conflict decisions,
idempotency, mutation ordering, checkpoint advancement, and aggregate receipts. Provider ports own
only provider reads, writes, serialization, identity, readback, and provider-specific errors.
Planning is side-effect free. Application requires attended authorization bound to the exact plan
digest and mutation set.

The numbered workflow modules and legacy compatibility package are removed from the v6 wheel and
source distribution. Their historical meaning remains in the archival mapping, migration guide,
rollback guide, immutable v5.6 release, and Git history.

## Stability determination

The retirement gate is satisfied objectively:

- v5.6.0 completed Full Validation V4V-32 and final publication/restoration run 30140577467;
- all 33 v5.6 publication checksums and both restored benchmarks passed;
- semantic and compatibility paths were differential-tested through the v5.2–v5.6 compatibility
  releases;
- v5.6.0 is immutable, installable, independently restorable, and the prospective v6 rollback;
- v6 changes provider policy and package ownership, not provider record formats or authority;
- checkpoints retain stable event identities and have an integrity-protected v2 representation;
- no unresolved compatibility, provider-state, or rollback defect exists.

No elapsed-time proxy is used because no live policy defines one.

## Consequences

This major release intentionally removes numbered imports and numbered CLI ownership. Consumers
must use the semantic replacements in the v6 migration guide. Rollback restores the removed
interfaces by installing immutable v5.6; v6 carries no hidden aliases.

Production activation, the final non-draft release, authority changes, and actual post-promotion
reconciliation remain Ryan-only decisions.
