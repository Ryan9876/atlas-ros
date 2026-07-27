# Atlas ROS Python Platform — v6.2.0

Atlas ROS is the governed executable core for the Atlas Ryan Operating System.

- **GitHub** is canonical for source, architecture, policy, schemas, runbooks, release manifests, packages, checksums, SBOMs, validation evidence, restoration assets, and immutable release history.
- **Notion** is the dynamic management authority for operating records, decisions, risks, integrations, automation state, and review evidence.
- **Todoist** is the attended execution authority for Ryan-owned executable work.
- **SQLite** is non-authoritative temporary runtime state.

## Active authority

- Active production release: **Atlas ROS v6.2.0**
- Production source and immutable tag target: `863d5ddf9ebd4723200166cf31c7acd93ebec54f`
- Immediate immutable rollback: **Atlas ROS v6.1.1** at `e1b842765376c9e36bbdee981cddead3feb97173`
- Final release: `v6.2.0`

## Capability-based architecture

Atlas ROS v6 retired numbered workflow ownership. Current capabilities include:

1. Capture
2. Adaptive Input Processing
3. Canonical Intent and Intent Partitioning
4. Outcome Recognition and Intent Graph construction
5. Archetype and Domain Knowledge Composition
6. Dependency Discovery and Constraint Propagation
7. Multidimensional Confidence and Dynamic Risk
8. Clarification, Current-Path Projection, and Reflection
9. Management Reasoning and Record Routing
10. Execution Planning and Decomposition
11. Attended Authorization and Execution Orchestration
12. Provider Adapters, Readback, Receipts, and Canonical Reconciliation

Reasoning and planning remain provider-free. Provider writes require a separate execution plan, exact attended authorization, immutable command generation, provider readback, and reconciliation.

## Safety and authority boundaries

Write-capable operations fail closed when authority, scope, constraints, exact-plan authorization, provider-object budget, or readback cannot be verified. The platform does not embed production credentials or private signing material. Autonomous scheduling, messaging, email, calendar actions, deletion, live network changes, and unattended consequential automation remain inactive.

## Execution controls

- Todoist contains only Ryan-owned executable management outcomes and independently completable current checkpoints.
- Portfolio Projects remain outcome-management records in Notion; a high-confidence Ryan-accountable project normally derives a current Action Record and execution path.
- Delegated technical implementation remains in Notion Delegated Work or dependency context rather than Ryan's personal execution queue.
- Parent tasks and subtasks use explicit Objective and Done When contracts.
- Execution planning is provider-neutral and digest-bound.
- Exact-plan authorization, deterministic commands, object budgets, idempotency, bounded retry, uncertain-apply readback, partial-failure handling, and fail-closed receipts are mandatory.
- Reconciliation cannot introduce work that was not present in the approved plan.

## Implemented CLI surface

`atlas initialize`, `atlas status`, `atlas capture`, `atlas decompose`, `atlas connectivity`, `atlas todoist reconcile`, `atlas release inventory`, `atlas release checksums`, and `atlas release verify`.

Commands not listed above are not part of the current executable surface.

## Validation

Atlas ROS v6.2.0 passed Exact-Artifact Full Validation V4V-44, governed final-publication controller validation V4V-45, and production-promotion verification V4V-46. The final release passed architecture validation, strict MyPy, Ruff, the complete branch-aware test suite, adaptive input processing, semantic fidelity, reasoning coherence, execution planning, execution orchestration, canonical reconciliation, knowledge management, clean installation, source restoration, v6.1.1 rollback restoration, checksums, SBOM identity, and zero-unauthorized-provider-write controls.

## Current documentation

- `release/RELEASE_MANIFEST.md`
- `release/RELEASE_SCOPE_V620.md`
- `release/RELEASE_NOTES_V620.md`
- `docs/runbooks/V620_OPERATOR_AND_RECOVERY.md`
- `docs/migration/V6_CANONICAL_CUTOVER_AND_W_RETIREMENT.md`
- `docs/architecture/TARGET_ARCHITECTURE.md`

Prior-version release evidence, restoration assets, ADRs, migration records, and validation artifacts are historical. They remain preserved but are not current operating authority.