# Atlas ROS v7.4.5 Runtime Performance Foundation Guide

## Purpose

The Runtime Performance Foundation reduces repeated provider reads, registry compilation, runtime composition, and unaffected operational recomputation without changing authority, authorization, provider readback, pipeline lineage, or rollback behavior.

## Operating sequence

1. Resolve live GitHub and Notion authority.
2. Load and verify the packaged runtime bundle or compile canonical source registries.
3. Select the command and compile a capability-scoped composition plan.
4. Collect semantic read requirements from participating capabilities.
5. Compile one provider-neutral operational read plan.
6. Execute exact provider reads sequentially through existing adapters.
7. Normalize all records and receipts into one immutable operation snapshot.
8. Run capability processing from that shared snapshot.
9. Plan incremental operational computation; broaden to full recomputation when uncertain.
10. Preserve existing planning, authorization, provider operation, readback, and receipt flows.

## Read planning

Capabilities declare record types, identities, required fields, relationships, pagination bounds, batching support, and conditional revisions. The planner unions fields and relationships, removes duplicate reads, and records conflicts. Adapters cannot remove requested evidence or decide semantic necessity.

Incomplete pagination, missing fields, contradictory records, unsupported batching, and provider limits are explicit. Unsafe conclusions fail closed or trigger broader reads under existing policy.

## Operation snapshots

`OperationReadSnapshotV1` is immutable, digest-bound, non-authoritative, and valid only for its operation. It records release identity, canonical and provider record identities, revisions, timestamps, missing fields, provenance, freshness, pagination, contradictions, and provider receipts.

Before any consequential write, Atlas revalidates applicable preconditions and target revisions. Existing exact authorization and mandatory readback remain unchanged.

## Verified runtime bundle and recovery

The build-once candidate workflow creates a bundle from authoritative package source. Runtime verification checks package version, source commit, architecture identity, source-file digests, compiler versions, registry digests, command bindings, and capability dependencies.

Recovery order:

1. Reject an invalid or mismatched bundle.
2. Run canonical source compilation.
3. Use the source result only when it validates and matches expected identities.
4. Fail closed when both paths are invalid.

Deleting the optimization bundle is safe because it can be rebuilt from governed package source.

## Capability-scoped composition

The runtime composes the smallest declared slice for the selected command. It broadens to full composition for incomplete dependency metadata, consequential commands, policy-declared broad impact, restoration, migration, shared execution or authorization changes, or release validation.

Operators can force full composition for diagnosis. Scoped and full outputs must remain equivalent.

## Incremental computation and full recomputation

Operational nodes are content-addressed by source, policy, contract, capability, dependency, authority, schema, and redaction identities. Changed nodes and transitive dependents recompute sequentially. A missing or corrupted prior index, incomplete graph, or identity mismatch triggers full recomputation.

The incremental index is disposable and non-authoritative. To recover, delete the index and run full recomputation. Periodic full verification remains available.

## Performance telemetry

Telemetry is redacted and behavior-neutral. It may report startup, bundle load, source compilation, composition, provider round trips, record counts, duplicate reads eliminated, snapshot construction, operational computation, memory, cache hits, rejection reasons, and p50/p95 fixture latency.

Do not report provider latency or bytes unless measured. Performance budgets cannot suppress correctness checks.

## Explicit exclusions

v7.4.5 does not implement:

- incremental pipeline or stage digest changes;
- concurrent, parallel, worker-pool, or asynchronous runtime processing;
- a resident daemon, attended warm session, cross-command connection pool, or retained authorization.

## Troubleshooting

- **Bundle rejected:** verify source commit, package version, architecture identity, compiler version, and all source and registry digests; use canonical source fallback.
- **Read plan incomplete:** inspect conflicting revisions, missing adapters, pagination limits, and provider receipts; broaden reads rather than truncating evidence.
- **Snapshot contradiction:** preserve all conflicting records and lower confidence or block conclusions according to policy.
- **Scoped composition uncertain:** force full composition and repair the dependency registry.
- **Incremental result uncertain:** discard the index and perform full recomputation.
- **Performance budget regression:** retain correctness behavior, capture variance and memory evidence, and block acceptance if the regression is material.

## Release boundary

The candidate workflow builds exact artifacts once, reuses them throughout validation, restores Active v7.4.0 and rollback v7.3.0, and produces a non-publishing controller receipt. Publication, tags, promotion, authority activation, live provider migrations, and production-record changes remain separately authorized by Ryan.
