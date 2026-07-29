# ADR-0076 — Per-Operation Immutable Read Snapshot

## Status

Proposed for v7.4.5 candidate validation.

## Decision

All participating capabilities in one Atlas operation receive the same immutable `OperationReadSnapshotV1`. The application layer compiles read scope, adapters perform exact sequential reads, and the coordinator normalizes records and receipts into one digest-bound snapshot.

Snapshots are non-authoritative, operation-bound, credential-free, and incapable of retaining authorization or execution intent. Missing fields, incomplete pagination, contradictions, source revisions, timestamps, provenance, and provider limitations remain explicit.

Before any consequential write, existing precondition and target-revision checks must run again, exact authorization must remain unchanged, and mandatory provider readback must complete.
