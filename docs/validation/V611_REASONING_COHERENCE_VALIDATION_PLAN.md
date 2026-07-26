# Atlas ROS v6.1.1 Validation Plan

## Baseline

Atlas ROS v6.1.0 remains Active. Atlas ROS v6.0.0 remains the immediate rollback until a separately authorized promotion.

## Release-blocking checks

- Ruff
- Architecture validation
- Strict MyPy
- Full pytest suite and existing coverage threshold
- Classification, knowledge-management, planning, orchestration, and reconciliation benchmarks
- Semantic Fidelity critical cases and 7/7 CloudVision invariance
- Reasoning Coherence corpus and contradiction tests
- Exact CloudVision parent and three current checkpoints
- Provider-free and shadow modes with zero provider writes
- Attended provider-canary object-budget validation
- Horizon re-evaluation with zero provider writes
- v6.1.0 differential compatibility
- Source and wheel builds, clean-wheel import, schemas, SBOM, dependency audit, and checksums
- Candidate restoration and rerun of semantic, coherence, planning, orchestration, and reconciliation benchmarks
- v6.1.0 rollback restoration

## Provider boundary

The candidate suite is provider-free. No attended provider canary is required because adapter behavior and provider scope are unchanged.

## Promotion boundary

Passing development and candidate validation does not activate production. Final promotion requires a separate exact authorization from Ryan.
