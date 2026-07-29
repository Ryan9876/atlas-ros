# ADR-0075 — Runtime Performance Foundation

## Status

Proposed for Atlas ROS v7.4.5 candidate validation. Production activation is separately authorized.

## Decision

Introduce an authority-neutral, sequential Runtime Performance Foundation after live authority resolution and verified runtime composition. The foundation may reduce duplicate provider reads, repeated registry compilation, unnecessary composition, and unaffected operational recomputation.

The canonical sequence remains:

1. Authority resolution.
2. Verified runtime composition.
3. Provider-neutral read planning.
4. Exact sequential provider reads.
5. Immutable operation snapshot.
6. Capability processing.
7. Existing planning and authorization.
8. Exact provider operation.
9. Mandatory readback and receipts.

## Included capabilities

- Per-operation immutable read snapshots.
- Provider read planning and request coalescing.
- Precompiled verified registry bundles.
- Governed performance contracts and telemetry.
- Capability-scoped runtime composition.
- Incremental content-addressed operational computation.

## Exclusions

The release does not change pipeline digest semantics, introduce concurrency or asynchronous execution, or create a resident warm session.

## Invariants

Cold execution, canonical source compilation, full composition, full recomputation, exact authorization, provider readback, deterministic output, and rollback restoration remain available. Optimization artifacts never become authority.
