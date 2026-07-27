# Atlas ROS v6.5 Production Operator and Recovery Runbook

Status: Current production operating guidance for Atlas ROS v6.5.0.

This runbook incorporates the compatible v6.2 operating baseline and adds the governed v6.5 execution-intelligence capabilities. Prior-version runbooks remain preserved for audit and rollback, but they are not current authority unless explicitly incorporated here or by the active manifest.

## Active authority

- Active release: Atlas ROS v6.5.0
- Production source and immutable tag target: `bb6d6fea70d6824c9bc6a42e63ba36cc88029260`
- Immediate immutable rollback: Atlas ROS v6.2.0 at `863d5ddf9ebd4723200166cf31c7acd93ebec54f`
- Historical rollback retained: Atlas ROS v6.1.1 at `e1b842765376c9e36bbdee981cddead3feb97173`
- Active manifest: `release/RELEASE_MANIFEST.md`
- Current documentation index: `docs/CURRENT_DOCUMENTATION.md`

## Initialization

1. Read the fixed Google Drive Release Index.
2. Read the Notion System State.
3. Read the active GitHub release manifest identified by the Release Index.
4. Read the Integration Inventory identified by the active manifest.
5. Confirm all four authorities agree on v6.5.0, the v6.2.0 rollback, required production integrations, and published-workspace validity.
6. Stop consequential work if any required authority is inaccessible, stale, or contradictory.

## Normal operation

1. Capture raw input without interpretation or provider writes.
2. Run Adaptive Input Processing and preserve semantic fidelity, responsibility, dependencies, constraints, confidence, clarification state, residual risk, current-path projection, and reflection evidence.
3. Compose only applicable governed frameworks. Preserve source, owner, effective scope, precedence, provenance, and conflicts. Fail closed when required framework dependencies or authority cannot be established.
4. Build the minimum effective path that satisfies the intended outcome while preserving mandatory controls, ordered prerequisites, rollback, escalation, and evidence requirements.
5. Generate Execution Intelligence from the canonical plan and verified evidence. It may describe readiness, friction, idempotency, retry, partial failure, readback status, and next valid actions; it cannot authorize, schedule, message, create tasks, or perform provider writes.
6. Produce a digest-bound human-readable presentation that separates facts, assumptions, warnings, blockers, decisions, and next steps and redacts sensitive values.
7. Use Scenario Intelligence only with immutable provider-neutral snapshots. Treat comparisons and counterfactuals as advisory; they cannot modify plans, tasks, authority, or live state.
8. Preserve digest-bound reasoning, framework, path, presentation, and execution-plan packages.
9. Do not invoke a provider unless a separate canonical execution plan and exact attended authorization exist.
10. Apply only the exact authorized commands within the approved provider-object budget.
11. Read every provider object back before reporting success.
12. Reconcile only verified provider state to authoritative Notion records. Reconciliation must not add work or reinterpret intent.

## Project-to-action responsibility rule

A Portfolio Project is an outcome-management record, not an execution object. When Ryan is accountable for a high-confidence project outcome, ROS normally:

1. Creates or updates the Portfolio Project.
2. Derives one current Ryan-owned management Action Record.
3. Separates delegated technical implementation from Ryan-owned management work.
4. Builds a bounded set of independently completable Ryan-owned checkpoints.
5. Creates or updates a Todoist parent and qualifying subtasks only after execution-readiness validation and attended authorization.
6. Reads back and reconciles the task tree.

A project may remain without a current Todoist action only when a governed reason is recorded, such as material clarification, no current horizon, no Ryan-owned action, duplicate representation, explicit deferral, unresolved hard constraint, high residual risk, or required review or authorization.

## Stop conditions

Stop before execution when any of the following is true:

- a current authority is inaccessible, stale, or contradictory;
- semantic fidelity, responsibility, routing, graph integrity, or reflection fails;
- a required framework is inapplicable, unauthoritative, conflicted, or missing a dependency;
- the minimum effective path omits a mandatory control, prerequisite, rollback, escalation, or evidence requirement;
- a material confidence dimension fails or material uncertainty remains unresolved;
- a hard constraint conflict or high residual risk exists;
- a presentation changes scope, hides a material assumption, or is not bound to the canonical plan;
- Scenario Intelligence is connected to live mutable state or treated as execution authority;
- the reasoning, framework, path, presentation, or execution-plan digest is invalid;
- exact attended authorization is absent or mismatched;
- the provider-object budget would be exceeded;
- a write cannot be verified by readback;
- reconciliation cannot preserve field authority, idempotency, and approved scope.

## Provider and authority boundaries

- Reasoning, framework composition, path planning, execution intelligence, presentation, and scenario analysis are provider-free.
- Todoist writes are attended, exact-plan authorized, and limited to Ryan-owned executable work.
- Notion owns dynamic management state, relationships, decisions, risks, integration state, automation state, and review evidence.
- Google Drive is the fixed initialization bootstrap and legacy historical release store.
- GitHub is canonical for source, policy, architecture, runbooks, release identity, validation evidence, restoration assets, and immutable software history.
- Google Calendar is contract-only and inactive.
- Outlook Email and Outlook Calendar are prohibited.
- Autonomous scheduling, messaging, email, deletion, live network changes, and unattended consequential automation are inactive.

## Recover from documentation or metadata drift

1. Stop consequential writes when a current authority surface contradicts the Release Index, System State, active manifest, or current documentation index.
2. Determine whether the affected object is mutable current guidance or immutable historical evidence.
3. Correct authorized mutable current records in place.
4. Mark obsolete mutable guidance `HISTORICAL — NOT CURRENT AUTHORITY` or place it under an explicit historical container.
5. Never rewrite immutable historical release, decision, validation, checksum, or restoration evidence.
6. Read every corrected surface back.
7. Run Quick Initialization again.
8. Run Full Validation for cross-authority audits, release work, recovery, or consequential architecture changes.

## Roll back production

Rollback requires Ryan's explicit authorization.

1. Confirm the fixed Release Index and current System State identify v6.2.0 as the immediate rollback.
2. Verify the immutable v6.2.0 source, release assets, checksums, and restoration evidence.
3. Stop v6.5 consequential execution.
4. Restore the exact v6.2.0 package and governed registries.
5. Update the Release Index, System State, active manifest, and current navigation surfaces transactionally.
6. Read all authority surfaces back.
7. Verify required integrations and provider boundaries.
8. Run rollback validation and record the decision and review evidence.

Do not infer rollback state from a prior runbook, historical title, candidate document, or chat history.

## Validation references

- Final promotion package validation: V4V-48
- Production publication and readback verification: V4V-49
- Promotion decision: V4D-36
- Final GitHub release: `v6.5.0`
- Active release manifest: `release/RELEASE_MANIFEST.md`
- Validated suite: 495 tests, 88.76% branch-aware coverage, and execution-planning benchmark 52/52
