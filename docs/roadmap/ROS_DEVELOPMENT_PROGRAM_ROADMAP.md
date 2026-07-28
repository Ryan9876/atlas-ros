# HISTORICAL — Atlas ROS Development Program Roadmap

Status: Superseded historical planning record. Current release and development authority are resolved through GitHub governance, the active release manifest, and current governed decisions. Production promotion remains Ryan-only.

## Purpose

This roadmap reconciles every current Atlas Development Idea and Atlas Development Initiative into the governed implementation sequence. It is the planning authority for development scope, sequencing, dependencies, regression preservation, and release traceability. It does not itself activate production changes.

## Final roadmap release designation

Completion of all approved roadmap waves is formally designated **Atlas ROS v6.0.0**.

Atlas ROS v5.2.0 remains the current Active production authority. Intermediate compatibility or incremental releases may be issued when required for phased delivery, validation, rollback safety, or migration control. This designation does not itself promote or activate v6.0.0; production promotion remains Ryan-only and requires the complete governed release process.

## Governing principles

- GitHub becomes the canonical software, documentation, release, validation, restoration, and recovery authority before modular architecture implementation begins.
- Notion remains live operational and management authority.
- Todoist remains attended execution authority.
- Existing production behavior is preserved through compatibility, differential testing, restoration validation, and immutable rollback.
- Ryan is the sole reviewer and production-promotion authority.
- Atlas has delegated authority to implement material improvements within approved programs, but cannot independently promote releases, activate unattended consequential automation, expand integrations, delete historical authority, or waive required quality and rollback evidence.

## Complete idea inventory and disposition

| Record | Title | Current disposition | Program treatment |
|---|---|---|---|
| ATI-1 | Classification Intelligence Evolution | Implemented / Approved | Implemented as a sequenced capability stream within the Management Reasoning Engine program. |
| IDEA-1 | Responsibility-Based Classification | Validated / Approved | Responsibility-first classification is active. |
| IDEA-2 | Classification Explainability | Validated / Approved | Evidence-aligned explainability is active. |
| IDEA-3 | Manager Intent Inference Engine | Planned / Approved | Phase 2C / later intelligence milestone. Added only after IDEA-1 and IDEA-2 validation. |
| IDEA-4 | Modular Cognitive Engines Architecture | Planned / Approved | Architectural source for knowledge composition, management structure, and modular engine boundaries. Implemented through IDEA-10. |
| IDEA-5 | Enforce Todoist Done When bullet formatting at the write boundary | Validated / Approved | Already delivered in v5.1. Preserved as a mandatory regression contract. |
| IDEA-6 | Todoist Section Routing by Management Domain | Validated / Approved | Delivered in v5.1 and preserved through the semantic Execution Planner, Orchestrator, and Todoist Adapter. |
| IDEA-7 | Preserve Todoist parent-subtask hierarchy during section moves | Validated / Approved | Already delivered in v5.1. Preserved as an adapter and reconciliation acceptance contract. |
| IDEA-8 | Release-Gated Development Record Reconciliation | Included as required next-release gate | Implemented in the GitHub-first authority migration before architecture cutover. |
| IDEA-9 | Task Economy and Execution Projection Guardrails | Planned / Approved | Mandatory Execution Planner design and release-blocking regression suite. |
| IDEA-10 | Capability-Based ROS Architecture Migration and W-Convention Retirement | Planned / Approved | Main phased implementation program after IDEA-11 promotion. |
| IDEA-11 | GitHub-First Authority Migration and Drive Dependency Reduction | Planned / Approved | Blocking prerequisite and first implementation program. |

## Release waves

### Wave 0 — GitHub-first authority and release-governance baseline

Primary records: IDEA-11 and IDEA-8.

Deliverables:

- Reconcile repository baseline to the active v5.1.1 source.
- Inventory and classify every Atlas Drive artifact.
- Migrate source-controlled documents, policies, schemas, release indexes, manifests, packages, checksums, SBOMs, validation evidence, restoration assets, and historical release evidence to GitHub.
- Implement GitHub Release publication and post-publication verification.
- Add a machine-readable implementation registry.
- Add bidirectional development-record reconciliation with Notion.
- Historical implementation note: the fixed Drive initialization bootstrap was preserved during the initial migration wave and was later removed from current initialization authority.
- Prove Active and rollback restoration without Drive release folders.
- Produce a promotion-ready authority-migration release candidate.

Exit condition: Ryan promotes the GitHub-first authority release after Full Validation.

### Wave 1 — Contract foundation and compatibility architecture

Primary records: IDEA-4 and IDEA-10.

Deliverables:

- Canonical component glossary and responsibility map.
- Versioned Capture, Reasoning, Knowledge, Management, Execution, Receipt, and Reconciliation contracts.
- Capability-based package boundaries.
- Semantic workflow orchestrators.
- Temporary W-number compatibility facades.
- Architectural fitness tests preventing engines from importing provider adapters.

Exit condition: no externally observable behavior change and all existing acceptance tests pass through compatibility facades.

### Wave 2 — Classification intelligence evolution

Primary records: ATI-1, IDEA-1, IDEA-2, and IDEA-3.

#### Phase 2A — Responsibility-first classification

- Implement `Responsibility -> Outcome -> Workstream -> Activity` as the primary classification hierarchy.
- Preserve project, operations, waiting, and development routing correctness.
- Add deterministic fixtures for people-leadership versus technical-activity ambiguity.

#### Phase 2B — Classification explainability

- Produce concise responsibility and workstream rationale for each decision.
- Preserve explanations in the Reasoning Package for governance and tuning.
- Expose low-confidence and challenged classifications without revealing unnecessary internal reasoning.

#### Phase 2C — Manager intent inference

- Add operating-context signals such as People Leader, Project Manager, Operations Manager, Strategic Planner, Individual Contributor, and Executive.
- Treat inferred context as an additional governed signal, never sole authority.
- Require confidence, evidence, explainability, and safe fallback.
- Enable only after 2A and 2B are stable.

Exit condition: the Management Reasoning Engine owns classification intelligence; record routing and provider writes remain separate.

### Wave 3 — Knowledge composition and management structure

Primary records: IDEA-4 and IDEA-10.

Deliverables:

- Planning Model registry.
- Knowledge Module registry and dependency resolution.
- Knowledge Composition Engine.
- Management Structure Engine.
- Deterministic Management Package generation.
- Team Operating Model end-to-end regression fixture.

Exit condition: complex management artifacts can be composed without creating execution objects.

### Wave 4 — Execution planning and task economy

Primary records: IDEA-9, with IDEA-5 and IDEA-6 as preserved regression contracts.

Deliverables:

- Provider-independent Execution Planner.
- Task Projection Test.
- Progressive execution horizon.
- Duplicate and existing-representation checks.
- Default one parent with zero to three meaningful subtasks; review gate above five.
- Explainability for projected and non-projected items.
- Regression proof that additional modules and artifact sections do not increase task count without additional independently executable Ryan-owned outcomes.

Exit condition: only the Execution Planner may propose execution objects, and no provider write occurs in the planner.

### Wave 5 — Execution orchestration and provider separation

Primary records: IDEA-10, preserving IDEA-5, IDEA-6, and IDEA-7.

Deliverables:

- Execution Orchestrator for authorization, sequencing, transaction state, idempotency, retries, and receipts.
- Todoist Adapter for provider-specific reads and writes only.
- Notion Adapter for provider-specific record operations only.
- Exact preservation of Objective, Done When, section-routing, hierarchy, and readback contracts.

Exit condition: provider logic cannot decide whether a task should exist, and all consequential writes produce verified receipts.

### Wave 6 — Reconciliation service and canonical cutover

Primary records: IDEA-8 and IDEA-10, preserving IDEA-7.

Deliverables:

- Execution Reconciliation Service.
- Field-level authority, command idempotency, checkpoint safety, conflict handling, and readback verification.
- Development-record reconciliation during release preparation and after promotion.
- Semantic workflows become canonical.
- W-number interfaces retire only after at least one stable compatibility release and verified rollback.

Exit condition: GitHub, Notion, release evidence, implementation registry, and production state agree, and the completed roadmap is eligible for governed promotion as **Atlas ROS v6.0.0**.

## Mandatory regression baseline

The following delivered capabilities cannot regress during any wave:

1. Todoist descriptions enforce the required Objective and Done When contract.
2. Management-domain section routing remains correct and explainable.
3. Parent-subtask hierarchy remains intact during moves and reconciliation.
4. Attended, review-first execution remains enforced.
5. Duplicate prevention, readback verification, rollback integrity, and historical authority preservation remain blocking controls.

## Traceability requirements

Every release candidate must include:

- referenced Idea and Initiative IDs;
- implementation disposition for each referenced record;
- implemented and remaining scope when partial;
- source commit and artifact digest;
- tests and acceptance evidence;
- migration and rollback evidence;
- machine-readable implementation registry;
- development-record reconciliation report;
- post-write and post-publication readback results.

A candidate cannot be recommended for promotion when this roadmap, the implementation registry, live Notion records, release manifest, or published artifacts disagree.
