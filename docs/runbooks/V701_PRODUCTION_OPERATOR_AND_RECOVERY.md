# Atlas ROS v7.0.1 Production Operator and Recovery Runbook

Status: Current production operating guidance for Atlas ROS v7.0.1.

This runbook incorporates the compatible v7.0.0 operating baseline and corrects the startup authority model. Prior-version runbooks remain preserved for audit and rollback and are not current authority unless explicitly incorporated here or by the active manifest.

## Active authority

- Active release: Atlas ROS v7.0.1
- Production source and immutable tag target: `f26f5154ea6cd4b431c5a2638c439d7de9282761`
- Immediate immutable rollback: Atlas ROS v6.5.0 at `bb6d6fea70d6824c9bc6a42e63ba36cc88029260`
- Historical rollback retained: Atlas ROS v6.2.0 at `863d5ddf9ebd4723200166cf31c7acd93ebec54f`
- Canonical authority: `governance/AUTHORITY.json`
- Generated Release Index: `governance/RELEASE_INDEX.md`
- Immutable manifest: `release/RELEASE_MANIFEST_V701.md` at the exact Active source commit
- Current manifest projection: `release/RELEASE_MANIFEST.md`
- Current documentation index: `docs/CURRENT_DOCUMENTATION.md`
- Promotion decision: V4D-41
- Exact package review: V4V-58
- Publication and activation review: V4V-59

## Initialization

1. Read `governance/AUTHORITY.json` from the canonical GitHub authority ref.
2. Verify its integrity digest and active release identity.
3. Read `governance/RELEASE_INDEX.md` from the same ref and verify the digest declared by `AUTHORITY.json`.
4. Read `release/RELEASE_MANIFEST_V701.md` from the exact immutable Active-release commit and verify its declared canonical digest.
5. Read the Notion System State URL named by `AUTHORITY.json`.
6. Read the Integration Inventory URL named by the immutable manifest.
7. Confirm all authorities agree on v7.0.1, v6.5.0 immediate rollback, required integration set, and published-workspace validity.
8. Confirm GitHub, Notion, and Todoist are connected, approved, accepted, current, and least-privilege verified.
9. Do not read or require Google Drive during initialization.
10. Stop consequential work if any required authority is inaccessible, stale, digest-invalid, or contradictory.

## Normal operation

1. Capture raw input without interpretation or provider writes.
2. Compile the applicable authority set from current live authorities and immutable release policy. Preserve source, owner, scope, precedence, provenance, and conflicts. Fail closed when authority cannot be established.
3. Run Adaptive Input Processing and preserve semantic fidelity, responsibility, dependencies, constraints, confidence, clarification state, residual risk, current-path projection, and reflection evidence.
4. Compose only applicable governed frameworks and preserve authority, provenance, precedence, dependencies, and conflicts.
5. Build the minimum effective path while preserving mandatory controls, ordered prerequisites, rollback, escalation, and evidence.
6. Generate Execution Intelligence only from the canonical plan and verified evidence. It cannot authorize, schedule, message, create tasks, or perform provider writes.
7. Produce a digest-bound human-readable presentation that separates facts, assumptions, warnings, blockers, decisions, and next steps.
8. Use Scenario Intelligence only with immutable provider-neutral snapshots.
9. Preserve digest-bound authority, reasoning, framework, path, presentation, and execution-plan packages.
10. Do not invoke a provider without a canonical execution plan and exact attended authorization.
11. Apply only exact authorized commands within the approved provider-object budget.
12. Read every provider object back before reporting success.
13. Reconcile only verified provider state. Reconciliation must not add work or reinterpret intent.

## Project-to-action responsibility rule

A Portfolio Project is an outcome-management record, not an execution object. When Ryan is accountable for a high-confidence project outcome, ROS normally:

1. Creates or updates the Portfolio Project.
2. Derives one current Ryan-owned management Action Record.
3. Separates delegated technical implementation from Ryan-owned management work.
4. Builds independently completable Ryan-owned checkpoints.
5. Creates or updates Todoist only after execution-readiness validation and attended authorization.
6. Reads back and reconciles the task tree.

A project may remain without a current Todoist action only when a governed reason is recorded.

## Stop conditions

Stop before execution when:

- a required current authority is inaccessible, stale, contradictory, or digest-invalid;
- authority compilation is incomplete or conflicted;
- semantic fidelity, responsibility, routing, graph integrity, or reflection fails;
- a mandatory framework, dependency, prerequisite, rollback, escalation, or evidence requirement is missing;
- material uncertainty, hard constraint conflict, or high residual risk remains;
- a presentation changes scope or hides a material assumption;
- Scenario Intelligence is connected to live mutable state or treated as execution authority;
- exact attended authorization is absent or mismatched;
- the provider-object budget would be exceeded;
- a write cannot be verified by readback; or
- reconciliation cannot preserve field authority, idempotency, and approved scope.

## Provider and authority boundaries

- GitHub owns canonical startup authority, source, architecture, policy, schemas, runbooks, release identity, immutable packages, validation evidence, restoration assets, and immutable software history.
- Notion owns dynamic management state, relationships, decisions, risks, integration state, automation state, and review evidence.
- Todoist writes are attended, exact-plan authorized, and limited to Ryan-owned executable work.
- Google Drive is optional non-authoritative legacy and historical storage. It is not read during initialization and is not a required integration.
- Google Calendar is contract-only and inactive.
- Outlook Email and Outlook Calendar are prohibited.
- Autonomous scheduling, messaging, email, deletion, live-network changes, credential actions, and unattended consequential automation are inactive.

## Drive historical boundary

1. Existing Drive content may remain available for optional historical reference.
2. Drive content does not determine Active release, rollback, startup authority, or integration readiness.
3. All v6.x and newer release records remain outside any deletion scope.
4. No Drive retirement, deletion, credential revocation, or historical cleanup may occur without separate exact authorization and verified exclusions.

## Recover from authority or metadata drift

1. Stop consequential writes when current authorities contradict one another.
2. Determine whether the affected object is mutable current guidance or immutable historical evidence.
3. Correct authorized mutable current records in place.
4. Never rewrite immutable historical release, decision, validation, checksum, or restoration evidence.
5. Read every corrected surface back.
6. Run GitHub-first Quick Initialization again.
7. Run Full Validation for cross-authority audits, release work, recovery, or consequential architecture changes.

## Roll back production

Rollback requires Ryan's explicit authorization.

1. Confirm `AUTHORITY.json`, the generated Release Index, and System State identify v6.5.0 as the immediate rollback.
2. Verify immutable v6.5.0 source, release assets, checksums, final identity, and restoration evidence.
3. Stop v7.0.1 consequential execution.
4. Restore the exact v6.5.0 package and governed registries.
5. Update GitHub authority, System State, current manifest, current documentation, Integration Inventory, and Automation Register transactionally.
6. Read all authority surfaces back.
7. Verify required integrations and provider boundaries.
8. Record rollback decision and validation evidence.

Do not infer rollback state from chat history, a prior runbook, historical title, candidate document, or release archive alone.
