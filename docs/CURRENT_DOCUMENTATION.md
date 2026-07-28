# Atlas ROS v7.0.1 Current Documentation Authority

Status: Current operating guidance for Atlas ROS v7.0.1.

Only the documents listed here, the canonical GitHub authority record and generated Release Index, the Notion System State, and authoritative application records for their owned fields may be treated as current operating guidance. Production status is determined by the active authority record and immutable manifest, not by historical wording.

## Release authority

- `governance/AUTHORITY.json`
- `governance/RELEASE_INDEX.md`
- `release/RELEASE_MANIFEST.md`
- `release/RELEASE_MANIFEST_V701.md`
- `release/RELEASE_NOTES_V701.md`
- `release/RELEASE_SCOPE_V701.md`
- GitHub Release `v7.0.1`
- Production source and immutable tag target: `f26f5154ea6cd4b431c5a2638c439d7de9282761`
- Immediate immutable rollback: Atlas ROS v6.5.0 at `bb6d6fea70d6824c9bc6a42e63ba36cc88029260`
- Historical rollback retained: Atlas ROS v6.2.0 at `863d5ddf9ebd4723200166cf31c7acd93ebec54f`
- Notion `Atlas ROS System State`
- Manifest-resolved Notion Integration Inventory

## Current architecture and policy

- `README.md`
- `docs/architecture/TARGET_ARCHITECTURE.md`
- `docs/adr/ADR-003-GITHUB-FIRST-AUTHORITY.md`
- `docs/adr/ADR-004-GITHUB-ONLY-INITIALIZATION.md`
- `docs/architecture/ADR-065-v650-governed-execution-intelligence.md`
- `docs/adr/ADR-010-SEMANTIC-INTENT-SEPARATION-AND-OUTPUT-FIDELITY.md`
- `docs/adr/ADR-011-REASONING-COHERENCE-AND-CONFIDENCE-DIMENSIONS.md`
- `governance/release-policy.yaml`

Immutable release scopes and prior ADRs may preserve pre-promotion or historical wording. Their architecture is incorporated only through the current authority record, active manifest, and this index.

## Current operations

- `docs/runbooks/V701_PRODUCTION_OPERATOR_AND_RECOVERY.md`
- `docs/EXECUTION_ORCHESTRATION_STANDARD.md`
- `docs/EXECUTION_RECONCILIATION_STANDARD.md`
- `docs/operations/EXECUTION_RECONCILIATION_RUNBOOK.md`
- `docs/CLASSIFICATION_INTELLIGENCE_STANDARD.md`

Prior-version runbooks are rollback and audit evidence, not current guidance.

## Current authority model

- GitHub: canonical source, architecture, policy, schemas, runbooks, release identity, validation evidence, restoration assets, immutable software history, and startup release authority.
- Notion: dynamic management records, decisions, risks, integration state, automation state, and review evidence.
- Todoist: attended execution state for Ryan-owned executable work.
- Google Drive: optional non-authoritative legacy and historical material; not read during initialization and not required.
- SQLite: non-authoritative temporary runtime state.

Required production integrations are exactly GitHub, Notion, and Todoist.

## Current capability terminology

Use capability names:

- Capture
- Adaptive Input Processing
- Authority Compilation
- Canonical Coordination
- Governed Operating Framework Composition
- Minimum Effective Path Planning
- Management Reasoning and Record Routing
- Execution Planning and Decomposition
- Execution Intelligence
- Human-Readable Execution Presentation
- Scenario Intelligence
- Attended Authorization and Execution Orchestration
- Provider Transactions, Readback, and Receipts
- Canonical Reconciliation

Do not use numbered workflow names as current runtime components.

## Historical documentation rule

Prior-version manifests, scopes, release notes, checksums, SBOMs, ADRs, restoration companions, promotion decisions, Review Records, candidate evidence, migration records, publication workflows, runbooks, and acceptance-test artifacts are preserved for history, audit, and rollback. They do not define current operations unless this index or the active manifest explicitly incorporates them.

Mutable superseded guidance must be marked `HISTORICAL — NOT CURRENT AUTHORITY` or placed under an explicit historical container. Immutable historical release evidence must remain unchanged.
