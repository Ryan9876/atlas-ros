# Atlas ROS Python Platform — v7.0.1

Atlas ROS is the governed executable core for the Atlas Ryan Operating System.

- **GitHub** is canonical for source, architecture, policy, schemas, runbooks, release manifests, packages, checksums, SBOMs, validation evidence, restoration assets, immutable release history, and startup release authority.
- **Notion** is the dynamic management authority for operating records, decisions, risks, integrations, automation state, and review evidence.
- **Todoist** is the attended execution authority for Ryan-owned executable work.
- **Google Drive** is optional, non-authoritative legacy and historical storage. It is not read during initialization and is not required for production operation.
- **SQLite** is non-authoritative temporary runtime state.

## Active authority

- Active production release: **Atlas ROS v7.0.1**
- Production source and immutable tag target: `f26f5154ea6cd4b431c5a2638c439d7de9282761`
- Immediate immutable rollback: **Atlas ROS v6.5.0** at `bb6d6fea70d6824c9bc6a42e63ba36cc88029260`
- Historical rollback retained: **Atlas ROS v6.2.0** at `863d5ddf9ebd4723200166cf31c7acd93ebec54f`
- Final release: `v7.0.1`
- Promotion decision: `V4D-41`
- Exact package validation: `V4V-58`
- Publication and authority activation: `V4V-59`

## GitHub-first initialization

1. Read and verify `governance/AUTHORITY.json` from GitHub.
2. Read and verify the generated `governance/RELEASE_INDEX.md` from the same authority ref.
3. Resolve the versioned immutable manifest from the exact Active-release commit and verify its canonical digest.
4. Read the Notion System State named by `AUTHORITY.json`.
5. Read the Integration Inventory identified by the immutable manifest.
6. Confirm GitHub, Notion, and Todoist are the exact required integrations and are connected, approved, accepted, current, and least-privilege verified.

Google Drive is not read during initialization and is not an initialization authority.

## Capability-based architecture

Atlas ROS uses capability ownership rather than numbered workflow ownership. Current capabilities include:

1. Capture
2. Adaptive Input Processing
3. Canonical Intent and Intent Partitioning
4. Outcome Recognition and Intent Graph Construction
5. Archetype and Domain Knowledge Composition
6. Dependency Discovery and Constraint Propagation
7. Multidimensional Confidence and Dynamic Risk
8. Clarification, Current-Path Projection, and Reflection
9. Authority Compilation
10. Canonical Coordination
11. Governed Operating Framework Composition
12. Minimum Effective Path Planning
13. Management Reasoning and Record Routing
14. Execution Planning and Decomposition
15. Execution Intelligence
16. Human-Readable Execution Presentation
17. Scenario Intelligence
18. Attended Authorization and Execution Orchestration
19. Provider Adapters, Readback, Receipts, and Canonical Reconciliation

Atlas ROS v7.0.1 preserves the v7 control plane while correcting startup authority. Authority compilation, reasoning, planning, presentation, and advisory analysis remain provider-free and digest-bound.

## Safety and authority boundaries

Write-capable operations fail closed when authority, scope, constraints, exact-plan authorization, provider-object budget, idempotency, or readback cannot be verified. Adapters cannot plan or authorize. Planning cannot authorize. Reconciliation cannot introduce execution intent. Autonomous scheduling, messaging, email, calendar actions, deletion, live-network changes, credential actions, and unattended consequential automation remain inactive.

## Execution controls

- Todoist contains only Ryan-owned executable management outcomes and independently completable current checkpoints.
- Portfolio Projects remain outcome-management records in Notion.
- Delegated technical implementation remains in Notion rather than Ryan's personal execution queue.
- Parent tasks and subtasks use explicit Objective and Done When contracts.
- Minimum-effective-path planning preserves mandatory controls, ordered prerequisites, rollback, escalation, and evidence.
- Exact-plan authorization, deterministic commands, object budgets, idempotency, bounded retry, uncertain-apply readback, partial-failure handling, and fail-closed receipts are mandatory.
- Reconciliation cannot introduce work that was not present in the approved plan.

## Implemented CLI surface

`atlas initialize`, `atlas status`, `atlas capture`, `atlas decompose`, `atlas connectivity`, `atlas todoist reconcile`, `atlas release inventory`, `atlas release checksums`, and `atlas release verify`.

Commands not listed above are not part of the current executable surface.

## Validation

Atlas ROS v7.0.1 passed exact corrective-package validation, complete security and quality validation, governed publication rehearsal, immutable GitHub publication, independent release-asset readback, clean installation, exact startup-authority validation, and rollback restoration. Required production integrations are GitHub, Notion, and Todoist exactly. Google Drive is not read during initialization.

## Current documentation

- `docs/CURRENT_DOCUMENTATION.md`
- `release/RELEASE_MANIFEST.md`
- `release/RELEASE_MANIFEST_V701.md`
- `release/RELEASE_NOTES_V701.md`
- `release/RELEASE_SCOPE_V701.md`
- `docs/runbooks/V701_PRODUCTION_OPERATOR_AND_RECOVERY.md`
- `docs/architecture/TARGET_ARCHITECTURE.md`
- `docs/adr/ADR-004-GITHUB-ONLY-INITIALIZATION.md`

Prior-version release evidence remains preserved for history and rollback. It is not current operating authority unless the active manifest or current documentation index explicitly incorporates it.
