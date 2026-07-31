# Atlas ROS v8.2.0 Draft Candidate Manifest

Status: exact candidate preparation only; not published, authorized, promoted, or active.

## Version derivation

Live authority identifies v8.1.0 as Active. This change adds backward-compatible production functionality without a breaking contract change, so the next unclaimed semantic minor version is v8.2.0.

## Candidate scope

- Composite Universal Inbox and Todoist ingress reconciliation aliases.
- Canonical parent/subtask Todoist comment-source events.
- Backward-compatible explicit `@atlas` parsing followed by bounded deterministic natural-language interpretation.
- Commitment, same-comment pronoun, Ryan follow-up, timezone-aware relative-date, outcome, and completion inference.
- Typed event evidence, dry-run provenance, exact plan/event authorization binding, readback, recovery, and replay.
- Existing-schema Notion ledger envelopes and additive local SQLite columns.
- One-active-Ryan-checkpoint enforcement and separate delegate-delivery/follow-up dates.
- Full regression compatibility with v8.1.0 context-aware clarification.

## Exact identity

The final candidate workflow must bind and retain:

- Exact source commit
- Source tree digest
- Source distribution and wheel SHA-256
- SPDX SBOM SHA-256
- Validation receipt and natural-comment evidence SHA-256
- Package/evidence checksum indexes
- Test count and total coverage
- Active v8.1.0 restoration evidence
- Immediate rollback v8.0.0 restoration evidence
- Provider write counts of zero during validation

These values are intentionally supplied by the build-once candidate workflow and must not be guessed or reconstructed.

## Schema and migration

No production Notion schema migration is required. The complete event envelope is stored in the existing reconciliation-state `Notes` field. Local SQLite schema evolution is additive and runtime-managed. Destructive operations: 0.

## Preserved boundaries

No autonomous scheduling, unattended provider write, messaging, email, calendar action, credential action, deletion, integration expansion, default-branch merge, immutable tag, GitHub Release, production authority activation, or production reconciliation apply is authorized by this candidate.
