# Atlas ROS v6.5 Current Documentation Authority

Status: Current operating guidance for Atlas ROS v6.5.0.

Only the documents listed here, the fixed active Release Index, the Notion System State, and authoritative application records for their owned fields may be treated as current operating guidance. Production status is determined by the active manifest, not by pre-promotion wording preserved inside immutable candidate or historical release artifacts.

## Release authority

- `release/RELEASE_MANIFEST.md`
- `release/RELEASE_NOTES_V650.md`
- GitHub Release `v6.5.0`
- Production source and immutable tag target: `bb6d6fea70d6824c9bc6a42e63ba36cc88029260`
- Immediate immutable rollback: Atlas ROS v6.2.0 at `863d5ddf9ebd4723200166cf31c7acd93ebec54f`
- Historical rollback retained: Atlas ROS v6.1.1 at `e1b842765376c9e36bbdee981cddead3feb97173`
- Fixed Google Drive `RELEASE_INDEX.md`
- Notion `Atlas/ROS System State — v6.5.0`

## Current architecture and policy

- `README.md`
- `docs/architecture/TARGET_ARCHITECTURE.md`
- `docs/architecture/ADR-065-v650-governed-execution-intelligence.md`
- `docs/migration/V6_CANONICAL_CUTOVER_AND_W_RETIREMENT.md`
- `docs/adr/ADR-010-SEMANTIC-INTENT-SEPARATION-AND-OUTPUT-FIDELITY.md`
- `docs/adr/ADR-011-REASONING-COHERENCE-AND-CONFIDENCE-DIMENSIONS.md`

ADR-065 and the immutable v6.5 release scope may preserve pre-promotion status language as historical decision evidence. Their architecture and scope are incorporated into v6.5.0 only through the active manifest and this index; their earlier status statements do not override current production authority.

## Current operations

- `docs/runbooks/V650_PRODUCTION_OPERATOR_AND_RECOVERY.md`
- `docs/EXECUTION_ORCHESTRATION_STANDARD.md`
- `docs/EXECUTION_RECONCILIATION_STANDARD.md`
- `docs/operations/EXECUTION_RECONCILIATION_RUNBOOK.md`
- `docs/CLASSIFICATION_INTELLIGENCE_STANDARD.md`

The v6.5 operator runbook incorporates compatible v6.2 baseline procedures and adds governed framework composition, minimum-effective-path planning, Execution Intelligence, human-readable execution presentation, and Scenario Intelligence. Prior-version runbooks are rollback and audit evidence, not current guidance.

## Current authority model

- GitHub: canonical source, architecture, policy, schemas, runbooks, release identity, validation evidence, and restoration assets.
- Notion: dynamic management records, decisions, risks, integration state, automation state, and review evidence.
- Todoist: attended execution state for Ryan-owned executable work.
- Google Drive: fixed initialization bootstrap and historical release records.
- SQLite: non-authoritative temporary runtime state.

## Current v6.5 capability terminology

Use capability names:

- Capture
- Adaptive Input Processing
- Governed Operating Framework Composition
- Minimum Effective Path Planning
- Management Reasoning and Record Routing
- Execution Planning and Decomposition
- Execution Intelligence
- Human-Readable Execution Presentation
- Scenario Intelligence
- Attended Execution Orchestration
- Provider Readback and Receipts
- Canonical Reconciliation

Do not use numbered workflow names as current runtime components.

## Historical documentation rule

Prior-version manifests, scopes, release notes, checksums, SBOMs, ADRs, restoration companions, promotion decisions, Review Records, candidate evidence, migration records, publication workflows, runbooks, and acceptance-test artifacts are preserved for history, audit, and rollback. They do not define current operations unless this index or the active manifest explicitly incorporates them.

Mutable superseded guidance must be marked `HISTORICAL — NOT CURRENT AUTHORITY` or placed under an explicit historical container. Immutable historical release evidence must remain unchanged. References to a prior release as Active are valid only inside clearly historical decision, validation, promotion, restoration, or audit context.