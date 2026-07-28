# Atlas ROS v7.1.0 Production Operator and Recovery Runbook

Status: Current production operating guidance for Atlas ROS v7.1.0.

This runbook governs normal operation, stop conditions, documentation-drift recovery, and rollback for the Active v7.1.0 release. Prior-version and candidate runbooks remain preserved for audit, packaging history, and authorized rollback. They are not current authority unless explicitly incorporated by the live canonical authority record, the exact immutable Active-release manifest, or the current documentation index.

## Active authority

- Active release: Atlas ROS v7.1.0
- Production source and immutable tag target: `0711b045f34f5ab7b03f7a61bc80653e0d815463`
- Immutable tag and GitHub Release: `v7.1.0`
- Immediate immutable rollback: Atlas ROS v7.0.1 at `f26f5154ea6cd4b431c5a2638c439d7de9282761`
- Historical rollback retained: Atlas ROS v6.5.0 at `bb6d6fea70d6824c9bc6a42e63ba36cc88029260`
- Historical rollback retained: Atlas ROS v6.2.0 at `863d5ddf9ebd4723200166cf31c7acd93ebec54f`
- Canonical authority: `governance/AUTHORITY.json`
- Generated Release Index: `governance/RELEASE_INDEX.md`
- Immutable manifest: `release/RELEASE_MANIFEST_V710.md` at the exact Active source commit
- Mutable current manifest projection: `release/RELEASE_MANIFEST.md`
- Current documentation index: `docs/CURRENT_DOCUMENTATION.md`
- Promotion decision: V4D-46
- Exact package review: V4V-66
- Prepublication review: V4V-67
- Independent publication readback: V4V-68
- Authority validation: V4V-69
- Final live authority readback: V4V-70

## Initialization

1. Read `governance/AUTHORITY.json` from the canonical GitHub authority ref.
2. Verify its integrity digest and exact Active-release identity.
3. Read `governance/RELEASE_INDEX.md` from the same ref and verify the digest declared by `AUTHORITY.json`.
4. Read `release/RELEASE_MANIFEST_V710.md` from exact immutable commit `0711b045f34f5ab7b03f7a61bc80653e0d815463` and verify its declared canonical digest.
5. Read the Notion System State URL named by `AUTHORITY.json`.
6. Read the Integration Inventory URL named by the immutable manifest.
7. Confirm all authorities agree on v7.1.0 Active, v7.0.1 immediate rollback, the required integration set, and published-workspace validity.
8. Confirm GitHub, Notion, and Todoist are connected, approved, accepted, production-current, and least-privilege verified.
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

## Recover from authority or documentation drift

1. Stop consequential writes when current authorities or current guidance contradict one another.
2. Determine whether the affected object is mutable current guidance or immutable historical evidence.
3. Correct only explicitly authorized mutable current records.
4. Never rewrite immutable historical release, decision, validation, checksum, or restoration evidence.
5. Read every corrected GitHub and Notion surface back.
6. Run GitHub-first Quick Initialization again.
7. Run Full Validation for cross-authority audits, release work, recovery, authority changes, integration-scope changes, or consequential architecture changes.
8. Record the governing decision and validation result in the authoritative Notion Decision Log and Review Records.

## Roll back production

Rollback requires Ryan's explicit authorization covering the exact rollback target and transaction.

1. Confirm `AUTHORITY.json`, the generated Release Index, the exact v7.1.0 immutable manifest, and System State identify v7.0.1 at `f26f5154ea6cd4b431c5a2638c439d7de9282761` as the immediate rollback.
2. Verify immutable v7.0.1 source, tag, GitHub Release assets, checksums, final identity, clean-install evidence, and restoration evidence.
3. Stop v7.1.0 consequential execution.
4. Restore the exact v7.0.1 package and governed registries without modifying immutable v7.1.0 or earlier historical records.
5. Update GitHub authority, generated Release Index, Notion System State, mutable current manifest projection, current documentation index, Integration Inventory, and Automation Register transactionally as required by the authorized rollback plan.
6. Read all authority and operating-guidance surfaces back in authoritative order.
7. Verify required integrations and provider boundaries without expanding scope.
8. Record the rollback decision and validation evidence.

Do not infer rollback state from chat history, a prior runbook, mutable summaries, historical titles, candidate documents, or release archives alone.
