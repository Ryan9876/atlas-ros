# Atlas ROS v6.2 Current Documentation Authority

Status: Current operating guidance for Atlas ROS v6.2.0.

Only the documents listed here, the active Release Index, the Notion System State, and authoritative application records for their owned fields may be treated as current operating guidance.

## Release authority

- `release/RELEASE_MANIFEST.md`
- `release/RELEASE_SCOPE_V620.md`
- `release/RELEASE_NOTES_V620.md`
- GitHub Release `v6.2.0`
- Immediate immutable rollback: Atlas ROS v6.1.1 (retained unchanged)
- Fixed Google Drive `RELEASE_INDEX.md`
- Notion `Atlas/ROS System State — v6.2.0`

## Current architecture and policy

- `README.md`
- `docs/architecture/TARGET_ARCHITECTURE.md`
- `docs/migration/V6_CANONICAL_CUTOVER_AND_W_RETIREMENT.md`
- `docs/adr/ADR-010-SEMANTIC-INTENT-SEPARATION-AND-OUTPUT-FIDELITY.md`
- `docs/adr/ADR-011-REASONING-COHERENCE-AND-CONFIDENCE-DIMENSIONS.md`

## Current operations

- `docs/runbooks/V620_PRODUCTION_OPERATOR_AND_RECOVERY.md`
- `docs/EXECUTION_ORCHESTRATION_STANDARD.md`
- `docs/EXECUTION_RECONCILIATION_STANDARD.md`
- `docs/operations/EXECUTION_RECONCILIATION_RUNBOOK.md`
- `docs/CLASSIFICATION_INTELLIGENCE_STANDARD.md`

## Current authority model

- GitHub: canonical source, architecture, policy, schemas, runbooks, release identity, validation evidence, and restoration assets.
- Notion: dynamic management records, decisions, risks, integration state, automation state, and review evidence.
- Todoist: attended execution state for Ryan-owned executable work.
- Google Drive: fixed initialization bootstrap and historical release records.
- SQLite: non-authoritative temporary runtime state.

## Historical documentation rule

Prior-version manifests, release notes, checksums, SBOMs, ADRs, restoration companions, promotion decisions, Review Records, candidate evidence, migration records, and acceptance-test artifacts are preserved for history, audit, and rollback. They do not define current operations unless this index or the active manifest explicitly incorporates them.

Mutable superseded guidance must be marked `HISTORICAL — NOT CURRENT AUTHORITY` or placed under a historical container. Retired numbered-workflow labels may appear only in historical, migration, compatibility-test, or immutable release-evidence contexts.

## Current runtime terminology

Use capability names:

- Capture
- Adaptive Input Processing
- Management Reasoning and Record Routing
- Execution Planning and Decomposition
- Attended Execution Orchestration
- Provider Readback and Receipts
- Canonical Reconciliation

Do not use numbered workflow names as current runtime components.
