# Atlas ROS v7.4.5 Runtime Performance Foundation — Implementation Prompt

## Instruction

Implement and prepare a non-publishing Atlas ROS **v7.4.5** release candidate that introduces a safe, release-controlled Runtime Performance Foundation. Use the permanent Feature Delivery Acceleration capabilities delivered in v7.4.0. Do not recreate those capabilities inside this release.

Finish in exactly one state:

- `IMPLEMENTATION READY FOR RYAN PROMOTION REVIEW`
- `READY WITH WARNINGS`
- `BLOCKED`

Promotion, publication, production tags, canonical authority activation, Notion System State changes, integration-scope changes, credentials, deletions, live provider migrations, and immutable-release modification remain reserved for Ryan.

## 1. Full Validation and release identity

Before editing:

1. Resolve live authority through Full Validation in the governed order.
2. Confirm exactly one Active release and the immediate rollback.
3. Read the exact immutable Active manifest and verify its declared digest when supported.
4. Read current Notion System State, Integration Inventory, Decision Log, Automation Register, Review Records, restoration guidance, rollback evidence, and relevant release assets.
5. Confirm GitHub, Notion, and Todoist are the exact required production integrations and are connected, approved, accepted, production-current, and least-privilege verified.
6. Confirm Google Drive is not required or read for authority resolution.
7. Determine the correct development baseline and verify that `7.4.5` is compatible with semantic-version and release-governance policy.

Stop `BLOCKED` on authority conflict, release-identity conflict, stale required authority, failed required integration, or rollback uncertainty.

## 2. Required Feature Delivery Acceleration dependency

Resolve and use, when present and compatible:

- `FeatureImplementationContractV1`
- `FeatureDefinitionOfDoneV1`
- canonical `atlas dev` validation commands
- change-impact and validation graph
- architecture-aware scaffolding
- shared scenario library and reusable transaction primitives
- declarative workflow registry
- build-once packaging
- traceability generation
- development-efficiency reporting

Create, validate, and digest the feature contract in `devtools/feature_delivery/contracts/v745-runtime-performance-foundation.yaml`.

Use impact-aware local validation and lean draft CI during development, but never allow impact analysis to suppress the complete final candidate gate. Freeze one exact candidate, build once, and reuse the exact artifacts throughout downstream validation.

If the foundation is unavailable or incompatible, do not duplicate it. Proceed only if current canonical tooling can provide equivalent safety and release quality; otherwise report the exact missing dependency and return `BLOCKED`.

## 3. Included and excluded scope

Implement only:

1. Per-operation immutable read snapshots
2. Provider read planning and request coalescing
3. Precompiled verified registry bundles
4. Governed performance contracts and telemetry
5. Capability-scoped runtime composition
6. Incremental content-addressed operational computation

Do not implement:

7. Incremental pipeline digest optimization
8. Bounded or asynchronous runtime concurrency
9. An attended warm-session or resident runtime

The release must improve performance without reducing authority verification, evidence completeness, deterministic behavior, provider safety, mandatory readback, rollback integrity, or candidate validation.

## 4. Preserved architecture

Preserve this sequence:

```text
Authority resolution
        ↓
Verified runtime composition
        ↓
Provider-neutral read planning
        ↓
Exact provider reads
        ↓
Immutable operation snapshot
        ↓
Capability processing
        ↓
Existing planning and authorization
        ↓
Exact provider operations
        ↓
Mandatory readback and receipts
```

Do not create a second execution planner, move semantic reasoning into adapters, allow reconciliation to create intent, cache authorization or execution intent, treat mutable provider content as permanent truth, bypass the canonical coordinator, weaken initialization, skip pre-write validation, or skip post-write readback.

## 5. Capability contracts

### 5.1 OperationReadSnapshotV1

Create an immutable, non-authoritative per-operation snapshot containing operation and correlation IDs, requested scope, authoritative release identity, normalized provider records, canonical references, source revisions and timestamps, requested and missing fields, pagination state, provenance, freshness, provider-read receipts, and a deterministic digest.

Compile read scope first, read each required record once where possible, normalize responses, explicitly preserve missing and contradictory evidence, and supply one coherent snapshot to all participating capabilities.

A snapshot may not retain credentials, authorization, or execution intent; may not be reused across operations without revalidation; and may not support a consequential write after stale preconditions. Before any write, revalidate preconditions and target revision, preserve exact authorization, and perform mandatory readback.

### 5.2 OperationalReadPlanV1

Create a provider-neutral read plan containing requesting capabilities, record types and identities, fields, relationships, providers, bounded pagination, batching opportunities, duplicates removed, conditional-read information, expected read count, and a deterministic digest.

The application layer determines semantic evidence requirements, unions fields and records, deduplicates reads, combines compatible traversals, and broadens uncertain scope. Adapters translate, batch where supported, paginate, select fields, and return receipts. Adapters may not decide semantic necessity, suppress fields, infer state, rank records, or authorize writes.

Incomplete or truncated evidence must be explicit, lower confidence where material, block unsafe conclusions, and trigger broader reads when policy requires.

### 5.3 VerifiedRuntimeBundleV1

During candidate packaging, deterministically compile and validate policy, contract, capability, schema, command-binding, dependency, and architecture registries. Bind source commit, package version, compiler versions, source-file digests, registry digests, and bundle digest. Include the bundle in the exact package.

At runtime, verify package/source identity and all governed digests. Use the bundle only when valid. Fall back to canonical source compilation when safe. Fail closed when neither path is valid.

Prove source compilation and verified-bundle equivalence for registry contents, digests, command bindings, dependencies, and policy behavior. The bundle is an optimization artifact, never authority.

### 5.4 Performance governance

Create:

- `PerformanceBudgetV1`
- `PerformanceObservationV1`
- `ProviderReadMetricsV1`
- `RuntimeCompositionMetricsV1`
- `IncrementalComputationMetricsV1`
- `PerformanceValidationReportV1`

Measure initialization, bundle loading, source compilation, scoped composition, provider round trips and bytes where measurable, records requested/returned, duplicates eliminated, snapshot construction, work-state and commitment computation, brief/context generation, incremental nodes evaluated, full recomputation, memory, bundle/cache hits, bundle rejection reasons, and p50/p95 latency.

Budgets must be versioned, evidence-based, configurable, fail-safe, and incapable of suppressing correctness checks. Telemetry must contain no secrets, credentials, authorization payloads, or unnecessary provider content and must never influence authority or execution results. Do not fabricate connector latency or byte savings.

### 5.5 RuntimeCompositionPlanV1

Create a machine-readable dependency graph:

```text
command → capability → contracts → policies → schemas → ports → adapters
```

The plan must identify selected command, requested and required capabilities, contracts, policies, schemas, ports, adapters, broadening reasons, full-composition requirement, and digest.

Compose the minimum verified runtime slice only after command selection. Preserve global identities, broaden when declarations are uncertain, and use full composition for consequential operations, restoration, migration, shared authorization/execution changes, inconsistent metadata, incomplete graphs, broad-impact policy, and release validation.

Prove scoped/full composition equivalence for all externally observable outcomes. Never omit policy, evidence, contracts, safeguards, or alter command semantics.

### 5.6 Incremental operational computation

Create:

- `OperationalComputationNodeV1`
- `OperationalDependencyEdgeV1`
- `OperationalComputationGraphV1`
- `IncrementalComputationPlanV1`
- `IncrementalComputationReceiptV1`

Node identity must bind canonical record ID, source revision, normalized content digest, policy digest, contract version, capability version, and dependency digests.

Compare current normalized identities with a prior non-authoritative index, identify changed nodes and transitive dependents, recompute affected nodes, reuse results only when every identity matches, emit a receipt, and fall back to full recomputation whenever impact is uncertain.

Invalidate on source, content, policy, contract, capability, dependency, authority, redaction, or schema changes. Persisted indexes must be disposable, bounded, versioned, digest-bound, rebuildable, and contain no credentials, authorization, execution intent, or mutable provider truth treated as permanent state.

Prove incremental/full recomputation equivalence across deterministic and randomized scenarios. Retain periodic full verification.

## 6. Explicit exclusions

Prove by code, architecture, and tests that v7.4.5 does not:

- change canonical stage-digest semantics, coordinator serialization, stage-result contracts, or lineage format;
- add concurrent provider reads, parallel capability execution, worker pools, async runtime conversion, or parallel operational computation;
- add a resident daemon, persistent interactive runtime, cross-command connection pooling, retained authorization, session-scoped mutable state, or long-running Atlas process.

All new behavior remains sequential and deterministic.

## 7. Implementation phases

1. Authority, dependency, baseline, architecture, read-duplication, registry, composition, and computation inventory; complete traceability.
2. Behavior-neutral performance contracts and baseline instrumentation.
3. Read requirement declaration, planning, coalescing, snapshots, receipts, and capability consumption.
4. Deterministic verified registry bundle, verifier, fallback, and equivalence tests.
5. Dependency registry, scoped composition, broadening, fallback, and equivalence tests.
6. Content-addressed graph, invalidation, incremental index, planner, receipts, and equivalence tests.
7. Integration, regression, provider-write boundary, restoration, and explicit-exclusion testing.
8. Frozen candidate, build-once exact artifacts, complete final gate, and non-publishing candidate package.

## 8. Mandatory scenarios

Implement deterministic coverage for all 51 scenarios specified by the governing v7.4.5 package plan, including duplicate and overlapping reads, missing fields, revision changes, stale snapshots, contradictory responses, pagination and truncation, unsupported batching, valid/invalid bundles, digest and source mismatches, telemetry redaction and missing measurements, scoped/full composition and broadening, incremental invalidation/corruption/equivalence, unchanged stage digests, no concurrency, no async conversion, no resident session, and no retained authorization.

Maintain a numbered scenario-to-test traceability matrix from `V745-001` through `V745-051`.

## 9. Stability and acceptance

Prove unchanged command semantics, authority resolution, write authorization, readback, reconciliation, pipeline lineage, cold execution, restoration behavior, and rollback eligibility. Prove safe bundle fallback, disposable incremental indexes, full composition, and full recomputation.

Measure baseline, unoptimized, optimized, full-computation, and incremental paths. Establish final thresholds from measured baseline and variance rather than arbitrary percentages. Acceptance requires measurable improvement in affected workloads, equal canonical output, no provider-write increase, no material startup regression, no memory regression beyond governed tolerance, and no reduction of final validation.

## 10. Complete candidate validation

The exact frozen candidate must pass Ruff, strict MyPy, architecture validation, complete branch-aware pytest, deterministic replay, read-plan and snapshot validation, bundle/source equivalence, scoped/full composition equivalence, incremental/full computation equivalence, corruption and invalidation tests, provider-write prohibition, authorization/readback/reconciliation regression, dependency policy, secret scanning, PyPI and OSV audits, clean source and wheel installs, runtime identity, CLI smoke tests, performance comparison, SBOM, source manifest, nested checksums, exact-artifact validation, Active restoration, immediate-rollback restoration, and non-publishing final-controller validation.

Development-time selective testing may not replace the complete final candidate tier.

## 11. GitHub Actions controls

Use one draft implementation PR, local-first focused validation, coherent commits, meaningful pushes, lean draft CI, path-filtered specialized workflows, safe stale-run cancellation, pinned dependency caching, one complete branch validation, one frozen candidate, one build, artifact reuse, and full CI only for the frozen candidate. Report runs used and avoided, cancellations, cache effectiveness, reused artifacts, duplicate builds avoided, and local validation before push.

## 12. Deliverables

Produce the ADRs, architecture/responsibility catalog changes, contracts, schemas, registries, implementations, fixtures, equivalence/corruption/invalidation/regression/benchmark tests, operator and recovery guides, Feature Delivery Acceleration usage record, feature contract, Definition of Done receipt, impact and traceability reports, performance and compatibility reports, security and Full Validation reports, Actions report, exact package, source/wheel hashes, SBOM, source manifest, nested checksums, restoration evidence, and draft PR.

## 13. Final report

Report:

- completion state;
- live authority baseline;
- acceleration components used;
- exact candidate identity;
- included capability matrix;
- explicit confirmation that exclusions 7, 8, and 9 were not implemented;
- provider-read, composition, registry-compilation, and recomputation results;
- equivalence results;
- p50/p95 and memory results;
- provider-write count;
- Actions utilization, build count, and artifact reuse;
- validation and restoration results;
- warnings;
- decisions reserved for Ryan.

Explicitly confirm no reduction of authority verification or provider readback; no pipeline-digest change; no concurrent execution; no resident warm session; no production authority modification; no publication; no live provider migration; no credential or integration expansion; and no immutable-release modification.

`IMPLEMENTATION READY FOR RYAN PROMOTION REVIEW` is permitted only when all six capabilities, all equivalence and mandatory gates, measurable improvements, exact artifacts, and rollback restoration pass while production remains unchanged. `READY WITH WARNINGS` requires all safety/correctness gates and only non-blocking findings with mitigations. Otherwise return `BLOCKED` with the exact dependency, gate, evidence, attempted repair, and Ryan decision required.