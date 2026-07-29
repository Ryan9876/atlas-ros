# ADR-0074: Feature Delivery Acceleration Foundation

Status: Proposed for Atlas ROS v7.4.0 candidate validation

## Decision

Create a bounded development-tooling layer under `atlas_ros.devtools_cli` and expose it only through `atlas dev`. The layer owns feature contracts, validation orchestration, shadow impact analysis, scaffolding foundations, traceability, and development reporting. Production runtime modules may not import it.

## Safety

- v7.4.0 impact analysis remains shadow-only.
- Unknown, governance, dependency, workflow, shared-contract, adapter, release, or architecture changes broaden validation.
- Mandatory candidate gates cannot be suppressed.
- Contracts cannot authorize production writes, migrations, promotion, scheduling, messaging, deletion, credential changes, or permission expansion.
- Manual validation and packaging fallback remains supported.

## Reuse from PR #63

Reuse the established lean/full CI separation, build-once artifact principle, deterministic validation receipts, zero-provider-write checks, and restoration evidence model. Do not reuse stale v7.1.1 Active-release assumptions or branch-specific workflow conditions.

## Rollout

1. Additive contracts, orchestrator, receipts, fixtures, traceability, and documentation.
2. Shadow impact analysis while established validation continues.
3. Controlled CI optimization only after shadow comparisons demonstrate no missed dependencies.
4. Scaffolding and workflow generation only after template governance and architecture validation mature.

## Consequences

Future features gain a stable implementation contract and one validation interface. Candidate quality requirements, rollback, immutable authority, provider boundaries, and Ryan-reserved promotion decisions remain unchanged.
