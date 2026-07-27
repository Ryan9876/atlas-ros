# Atlas ROS v6.5.0 Release Scope

## Status

Release candidate preparation only. Atlas ROS v6.2.0 remains the sole Active production release and Atlas ROS v6.1.1 remains its immutable rollback. No promotion, tag, GitHub Release, Release Index, System State, or integration record change is authorized by this document.

## Included capabilities

1. Governed Operating Framework Composition
2. Minimum Effective Path Planning
3. Execution Intelligence
4. Human-Readable Execution Presentation
5. Scenario Intelligence

All five capabilities are provider-free, typed, deterministic, digest-bound, advisory-only, and fail closed. They cannot create, update, delete, schedule, message, authorize, execute, or train online.

## Compatibility and rollback

The v6.2 input-processing, planning, orchestration, adapter, and reconciliation contracts remain unchanged when v6.5 is unused. v6.5 contract evolution is additive. The candidate validation must prove clean installation, source restoration, v6.2.0 active-release restoration, and v6.1.1 historical rollback restoration. Promotion, if later authorized, makes v6.2.0 the immediate immutable rollback.

## Candidate gates

The exact candidate must pass Ruff, architecture validation, strict MyPy, dependency security, secret scanning, branch-aware pytest coverage, package build, clean wheel installation, source restoration, release artifact checksums, rollback installation, and zero-provider-write checks. A draft candidate is not production-ready until the exact-candidate workflow records those results and an independent release review is complete.
