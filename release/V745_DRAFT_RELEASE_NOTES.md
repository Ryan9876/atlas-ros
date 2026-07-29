# Atlas ROS v7.4.5 Draft Release Notes

Atlas ROS v7.4.5 introduces a Runtime Performance Foundation that reduces repeated provider reads, repeated registry compilation, unnecessary runtime composition, and unaffected operational recomputation while preserving complete authority verification, deterministic outputs, exact authorization, provider readback, full fallbacks, and rollback integrity.

## Added

- `OperationReadSnapshotV1` and one-snapshot-per-operation coordination.
- `OperationalReadPlanV1` with field union, deduplication, bounded pagination, conditional revision reporting, and sequential adapter execution.
- `VerifiedRuntimeBundleV1`, deterministic bundle compiler, identity verification, and canonical source fallback.
- Governed performance budgets, observations, provider-read metrics, runtime-composition metrics, incremental-computation metrics, and aggregate validation reports.
- Machine-readable capability-scoped composition plans with conservative full-composition broadening.
- Content-addressed operational computation graphs, disposable incremental indexes, transitive invalidation, and full-recomputation fallback.
- Dedicated build-once non-publishing candidate workflow, exact artifact checksums, SBOM, source manifest, clean installs, and Active/rollback restoration.

## Unchanged

- Canonical pipeline and stage digest semantics.
- Sequential runtime execution.
- Cold execution and existing optional immutable cache categories.
- Authority resolution, provider-write authorization, reconciliation, mandatory readback, and release validation.

## Not included

- Incremental pipeline digests.
- Bounded runtime concurrency or asynchronous conversion.
- An attended warm session or resident runtime.

## Production status

Draft only. This candidate is not published, tagged, promoted, merged, or active. Ryan retains the exact-package promotion decision.
