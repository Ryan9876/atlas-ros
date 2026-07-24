# Atlas ROS Python Platform — v5.5.0rc1

Atlas ROS is the governed executable core for the Atlas Ryan Operating System.
GitHub is the canonical release and runtime authority, Notion is the dynamic
management authority, Todoist is the attended execution provider, and SQLite is
non-authoritative local runtime state.

## Safety

Write-capable commands default to dry-run or require explicit confirmation. The platform does not embed production credentials or private signing material. Autonomous scheduling, messaging, email, calendar actions, deletion, and unattended consequential automation remain inactive.

## Core controls

- Exact Todoist `**Objective:**` and `**Done when:**` description contract for parent tasks and subtasks.
- Full-field W03 creation, repair, ordering, validation, and readback.
- Retry-safe W04 reconciliation with snapshot-consistent checkpoints.
- Governed risk, blocker, dependency, and issue synchronization.
- Explicit delegation review without falsely requiring delegated work for every Ryan-owned action.
- Unblock commands resolve one existing open blocker and fail safely when the target is absent or ambiguous.
- ISO-date validation for checkpoints and content validation for blocker commands.
- Durable SQLite/outbox behavior, redacted adapter failures, and provider-host restrictions.
- Deterministic dependency locking, canonical source manifests, SBOM, checksums, and retained CI evidence.
- Provider-neutral Execution Candidate, Projection Decision, and Execution Plan
  V2 contracts with digest-bound provenance.
- Progressive execution horizons, layered duplicate suppression, verified
  existing-representation matching, and a governed 0–3 / 4–5 / review task budget.
- Architecture enforcement that keeps planning outside provider writes,
  authorization, execution, receipt generation, and orchestration.

## Implemented CLI surface

`atlas initialize`, `atlas status`, `atlas capture`, `atlas decompose`, `atlas connectivity`, `atlas todoist reconcile`, `atlas release inventory`, `atlas release checksums`, and `atlas release verify`.

Commands not listed above are not part of the current executable surface.

## Validation

The v5.5.0 release candidate must pass Ruff, strict MyPy, architecture
validation, the complete test suite with branch coverage above 85%, the
release-blocking Execution Planning benchmark, source and wheel builds,
clean-wheel installation, packaged configuration smoke testing, dependency-lock
validation, vulnerability audits, canonical source-manifest verification,
checksum-bound draft staging, and Drive-independent restoration before
promotion.

See `docs/operations/OPERATIONS_RUNBOOK.md`, `docs/migration/MIGRATION_PLAN.md`, and `release/RELEASE_MANIFEST.md`.
