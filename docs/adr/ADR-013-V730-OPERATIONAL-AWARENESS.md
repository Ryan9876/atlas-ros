# ADR-013 — Atlas ROS v7.3 Operational Awareness

Status: Candidate. No production activation is authorized.

## Decision

Create a bounded, provider-neutral Operational Awareness subsystem that transforms authorized records into immutable evidence, snapshots, work-state estimates, commitment assessments, exception briefs, context packs, resumption points, work graphs, hygiene findings, and repair proposals.

## Boundaries

- Awareness is read-only and proves zero provider writes in every stage receipt.
- Capabilities are separately registered and independently testable.
- Policy is declarative, schema-validated, digest-bound, replayable, and fail closed.
- Adapters only normalize authorized reads. They do not infer, rank, plan, authorize, or repair.
- Repair proposals must enter canonical planning and attended authorization before any provider operation.
- Reconciliation remains unable to create successor intent.
- Google Drive is not a runtime or release authority.

## Processing order

Snapshot normalization → work-state estimation → commitment assessment → material-change detection and brief → execution context → work-graph hygiene.

## Consequences

Ryan can inspect material exceptions and resume work without reconstructing the full system. Deterministic evidence and freshness remain visible, and stale or contradictory state cannot silently become completion.
