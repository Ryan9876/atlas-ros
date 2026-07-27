# Atlas ROS Python Platform — v6.5.0

Atlas ROS is the governed executable core for the Atlas Ryan Operating System.

- **GitHub** is canonical for source, architecture, policy, schemas, runbooks, release manifests, packages, checksums, SBOMs, validation evidence, restoration assets, and immutable release history.
- **Notion** is the dynamic management authority for operating records, decisions, risks, integrations, automation state, and review evidence.
- **Todoist** is the attended execution authority for Ryan-owned executable work.
- **Google Drive** provides the fixed initialization Release Index and preserves legacy historical release records.
- **SQLite** is non-authoritative temporary runtime state.

## Active authority

- Active production release: **Atlas ROS v6.5.0**
- Production source and immutable tag target: `bb6d6fea70d6824c9bc6a42e63ba36cc88029260`
- Immediate immutable rollback: **Atlas ROS v6.2.0** at `863d5ddf9ebd4723200166cf31c7acd93ebec54f`
- Historical rollback retained: **Atlas ROS v6.1.1** at `e1b842765376c9e36bbdee981cddead3feb97173`
- Final release: `v6.5.0`

## Capability-based architecture

Atlas ROS v6 uses capability ownership rather than numbered workflow ownership. The v6.2 baseline capabilities remain active:

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

Atlas ROS v6.5.0 adds five separated, provider-free execution-intelligence capabilities:

1. Governed Operating Framework Composition
2. Minimum Effective Path Planning
3. Execution Intelligence
4. Human-Readable Execution Presentation
5. Scenario Intelligence

The v6.5 capabilities are additive. They improve evidence, planning, presentation, and advisory analysis without gaining provider, task, authorization, scheduling, messaging, deletion, or execution authority.

## Safety and authority boundaries

Reasoning, framework composition, path planning, execution intelligence, presentation, and scenario analysis remain provider-free. Write-capable operations fail closed when authority, scope, constraints, exact-plan authorization, provider-object budget, or readback cannot be verified. Autonomous scheduling, messaging, email, calendar actions, deletion, live network changes, and unattended consequential automation remain inactive.

## Execution controls

- Todoist contains only Ryan-owned executable management outcomes and independently completable current checkpoints.
- Portfolio Projects remain outcome-management records in Notion; a high-confidence Ryan-accountable project normally derives a current Action Record and execution path.
- Delegated technical implementation remains in Notion Delegated Work or dependency context rather than Ryan's personal execution queue.
- Parent tasks and subtasks use explicit Objective and Done When contracts.
- Governed frameworks must preserve applicability, authority, provenance, precedence, and conflicts.
- Minimum-effective-path planning must preserve mandatory controls, ordered prerequisites, rollback, escalation, and evidence.
- Human-readable execution presentation must remain digest-bound to the canonical plan and separate facts, assumptions, warnings, blockers, decisions, and next steps.
- Scenario Intelligence uses immutable provider-neutral snapshots and remains advisory.
- Exact-plan authorization, deterministic commands, object budgets, idempotency, bounded retry, uncertain-apply readback, partial-failure handling, and fail-closed receipts are mandatory.
- Reconciliation cannot introduce work that was not present in the approved plan.

## Implemented CLI surface

`atlas initialize`, `atlas status`, `atlas capture`, `atlas decompose`, `atlas connectivity`, `atlas todoist reconcile`, `atlas release inventory`, `atlas release checksums`, and `atlas release verify`.

Commands not listed above are not part of the current executable surface.

## Validation

Atlas ROS v6.5.0 passed Final Promotion Package Validation V4V-48 and Production Publication and Readback Verification V4V-49. The final package passed Ruff, architecture validation, strict MyPy, dependency and secret security, 495 tests with 88.76% branch-aware coverage, execution-planning benchmark 52/52, package construction, source checksums, SBOM identity, clean installation, exact-source restoration, v6.2.0 immediate rollback restoration, v6.1.1 historical rollback restoration, and zero-provider-write controls.

## Current documentation

- `docs/CURRENT_DOCUMENTATION.md`
- `release/RELEASE_MANIFEST.md`
- `release/RELEASE_NOTES_V650.md`
- `docs/runbooks/V650_PRODUCTION_OPERATOR_AND_RECOVERY.md`
- `docs/architecture/ADR-065-v650-governed-execution-intelligence.md`
- `docs/architecture/TARGET_ARCHITECTURE.md`
- `docs/migration/V6_CANONICAL_CUTOVER_AND_W_RETIREMENT.md`

Prior-version release evidence, scopes, restoration assets, ADRs, runbooks, migration records, workflows, and validation artifacts remain preserved for history and rollback. They are not current operating authority unless the active manifest or current documentation index explicitly incorporates them.