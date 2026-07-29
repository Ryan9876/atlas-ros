# Atlas ROS v7.4.5 Runtime Performance Traceability

## Capability and evidence map

| ID | Scenario | Primary evidence |
|---|---|---|
| V745-001 | Multiple capabilities request the same record | `test_read_plan_coalesces_duplicate_and_overlapping_requirements` |
| V745-002 | Overlapping fields are unioned | `test_read_plan_coalesces_duplicate_and_overlapping_requirements` |
| V745-003 | Missing provider field remains explicit | `test_snapshot_is_deterministic_and_preserves_missing_fields` |
| V745-004 | Provider revision changes during operation | snapshot revision and contradiction fixtures |
| V745-005 | Snapshot expires before write | operation-bound snapshot invariants and precondition policy |
| V745-006 | Contradictory provider responses | `test_snapshot_marks_contradictory_provider_content` |
| V745-007 | Cross-operation snapshot reuse rejected | `OperationReadSnapshotV1` boundary validation |
| V745-008 | Duplicate request elimination | read-plan unit and benchmark fixtures |
| V745-009 | Field union across capabilities | read-plan unit fixture |
| V745-010 | Bounded pagination | `ReadRequirementV1.pagination_limit` validation |
| V745-011 | Provider result truncation | snapshot pagination and coordinator incomplete-evidence gate |
| V745-012 | Unsupported batching | read-plan batching opportunity rules |
| V745-013 | Adapter returns incomplete evidence | coordinator incomplete-evidence gate |
| V745-014 | Unknown requirement broadens scope | full-read policy and incomplete requirement receipt |
| V745-015 | Valid bundle load | `test_runtime_bundle_build_verify_and_source_fallback` |
| V745-016 | Bundle digest mismatch | `test_verified_bundle_rejects_digest_mismatch` |
| V745-017 | Source commit mismatch | `RuntimeBundleVerifier` identity check |
| V745-018 | Policy digest mismatch | registry digest and source fallback validation |
| V745-019 | Missing bundle | canonical source fallback unit test |
| V745-020 | Safe source fallback | `test_runtime_bundle_build_verify_and_source_fallback` |
| V745-021 | Bundle/source equivalence | bundle compiler, verifier, and candidate validation report |
| V745-022 | Invalid source and bundle fail closed | `RuntimeBundleVerifier.load_or_compile` failure path |
| V745-023 | Baseline observation | fixture performance validator |
| V745-024 | Budget pass | `PerformanceBudgetV1` fixtures |
| V745-025 | Budget regression | full-candidate performance report and warning boundary |
| V745-026 | Missing measurement | optional measurement fields remain null |
| V745-027 | Telemetry redaction | `test_telemetry_is_behavior_neutral_and_redacted` |
| V745-028 | Provider-read count | `ProviderReadMetricsV1` benchmark report |
| V745-029 | No fabricated provider latency | provider metric validator and report flags |
| V745-030 | Simple read-only command | scoped composition unit fixture |
| V745-031 | Command requires adapter | scoped composition adapter fixture |
| V745-032 | Consequential command uses full composition | `test_consequential_or_incomplete_composition_broadens` |
| V745-033 | Missing dependency edge | incomplete declaration broadening |
| V745-034 | Policy-driven broadening | broad-impact composition flag |
| V745-035 | Scoped/full equivalence | `CapabilityScopedComposer.verify_equivalence` and performance validator |
| V745-036 | Unknown command | `test_unknown_command_fails_closed` |
| V745-037 | One changed leaf record | incremental planner fixtures |
| V745-038 | Parent dependency recomputation | transitive recomputation unit test |
| V745-039 | Brief recomputation | transitive recomputation unit test |
| V745-040 | No changes | reusable node planning behavior |
| V745-041 | Policy change invalidates dependents | computation identity policy digest |
| V745-042 | Contract version change | computation identity contract version |
| V745-043 | Missing edge forces full recomputation | incomplete graph fallback |
| V745-044 | Persisted index corruption | no-index full fallback and disposable-index policy |
| V745-045 | Incremental/full equivalence | performance validator and required full gate |
| V745-046 | Periodic full verification | documented full-recomputation procedure |
| V745-047 | Stage digest format unchanged | `validate_v745_exclusions.py` and non-publishing receipt |
| V745-048 | No concurrent provider calls | exclusion validator and sequential adapter protocol |
| V745-049 | No async runtime conversion | exclusion validator |
| V745-050 | No resident warm session | exclusion validator and ADRs |
| V745-051 | No authorization retained | snapshot, index, and non-publishing controller boundaries |

## Mandatory release gates

The exact frozen head must pass Ruff, strict MyPy, architecture validation, complete branch-aware pytest, deterministic replay, feature-contract compilation, all equivalence checks, corruption and invalidation tests, provider-write prohibition, authorization and readback regression, secret scan, PyPI and OSV audits, clean source and wheel installation, runtime identity, CLI smoke tests, performance reporting, SBOM, source manifest, nested checksums, Active v7.4.0 restoration, immediate rollback v7.3.0 restoration, and the non-publishing final controller.

## Feature Delivery Acceleration usage

- Contract: `devtools/feature_delivery/contracts/v745-runtime-performance-foundation.yaml`
- Lean draft workflow: focused lint, MyPy, tests, exclusions, contract compilation, and bundle compilation.
- Full candidate workflow: exact checkout, complete gates, build once, artifact reuse, security, performance, clean installs, restoration, and retained evidence.
- Impact analysis remains shadow-only and cannot suppress mandatory final gates.
