# Changelog

## 6.1.0rc1 - 2026-07-26

- Added first-class intent partitioning that separates primary business outcomes from current, delegated, conditional, evaluation, audit, provider-control, and reference instructions.
- Added Reasoning Package V4, Management Package V3, Execution Candidate/Decision/Plan V3, and Semantic Fidelity Result V1 contracts and schemas.
- Added reusable controlled-technology-pilot and single-business-outcome planning models.
- Added a fail-closed Semantic Fidelity Gate and expert golden/metamorphic benchmark.
- Preserved v6 orchestration, reconciliation, provider-separation, attended-authorization, and rollback boundaries.

# Unreleased — Execution Planning and Task Economy Phase 3

- Added immutable Execution Candidate, Projection Decision, Existing
  Representation Index, and Execution Plan V2 contracts.
- Added deterministic, model-agnostic candidate extraction from Management
  Package V2 with content-safe observability.
- Added the full Task Projection Test, progressive execution horizons, layered
  duplicate suppression, and provider-neutral existing-representation matching.
- Added governed 0–3 and justified 4–5 task budgets; more than five candidates
  require decomposition review and never authorize execution.
- Added independently validated multiple-parent proposals without artificial
  plan splitting.
- Preserved W03A and Execution Plan V1 compatibility through explicit safe
  projections that fail closed when V2 meaning would be lost.
- Added a 52-case release-blocking benchmark, JSON schemas, ADR-007, migration
  guidance, architecture gates, candidate evidence, and draft restoration tests.

## v5.4.0 — Knowledge Composition and Management Structure Phase 2

- Added versioned knowledge, planning-model, and module registries.
- Added deterministic dependency resolution and digest-bound provenance.
- Added provider-free Management Package V2 output and declarative Team
  Operating Model generation.

## v5.1.0 — Classification Intelligence Phase 1

- Added responsibility-first classification across People Leadership, Project Delivery, Operational Stewardship, External Dependency, and Capability Building.
- Added version 2 reasoning contracts with structured evidence, workstream, operating context, challenge state, fallback reason, and explicit version 1 projection.
- Added concise evidence-aligned classification explanations and manager-intent inference as a supporting signal only.
- Added shadow, attended, and explicit semantic W02 modes while preserving legacy mode as the default production-compatible path.
- Added governed policy configuration, a 30-case evaluation dataset, quantitative calibration tooling, implementation-registry traceability, ADR-005, and regression coverage.
- Preserved deterministic record routing, provider separation, attended execution, rollback controls, and Ryan-only production promotion.

## v5.0.0rc1 — Milestone 5

- Added governed evidence-first reasoning and recommendation engine.
- Added deterministic weighted tradeoff analysis, uncertainty propagation, abstention, explanations, and decision-quality evaluation.
- Added immutable RecommendationRecord generation and blocking regression coverage.

# Changelog

## 4.5.2 - 2026-07-21

- Add the complete executable Atlas ROS implementation and packaged policy configuration.
- Enforce exact bold `**Objective:**` and `**Done when:**` headings for Todoist parent tasks and subtasks.
- Create, repair, order, and fully read back governed Todoist task trees before synchronization succeeds.
- Make W04 command groups retry-safe and checkpoint advancement snapshot-consistent.
- Implement risk, blocker, dependency, and issue reconciliation with parent and Execution Step linkage.
- Add durable SQLite/outbox controls, adapter hardening, redacted errors, and provider-host restrictions.
- Add deterministic dependency locking, dual-service vulnerability auditing, SBOM, release checksums, and retained CI evidence.
- Validate with Ruff, strict MyPy, 58 tests, 86.30% branch coverage, clean package installation, and packaged-policy smoke testing.
- Designate Atlas ROS v4.5.1 as the immediate immutable rollback baseline.

## 4.5.0 - 2026-07-21

- Standardize Todoist Work sections as Leadership & Team, Active Projects, Operations, Waiting on Others, and Development & Learning.
- Define Waiting on Others as a temporary dependency state that returns to Operations or Active Projects when cleared.
- Add optional Execution Priority to Execution Steps; blank inherits the parent Action priority and explicit values override it.
- Add Execution State values Ready, In Progress, Waiting, Blocked, Delegated, Review, and Complete.
- Extend W04 commands with risk, dependency, and issue routing to the production Risks and Blockers database.
- Link governed risk records to both the parent Action and applicable Execution Step using Todoist comment ID idempotency.
- Preserve attended, review-first boundaries and designate v4.4.2 as the immediate immutable rollback.


## 4.4.2 - 2026-07-21

- Fixed W04 comment ingestion to read governed parent tasks and all linked subtasks.
- Added support for colon-form commands such as `@atlas update: text`.
- Fixed `@atlas delegate to <name>` parsing and Notion person resolution.
- Delegation commands now populate Assigned Person, Assigned Resource, Resource Type, parent Action linkage, and parent Todoist task linkage.
- Subtask update comments now write to the linked Execution Step rather than overwriting the parent Action update.
- Added regression tests for parent/subtask comments, delegation assignment, linkage, and idempotent replay.

## 4.4.1 - 2026-07-21

- Promote connector-native attended W04 reconciliation after cross-surface production acceptance.
- Share processed-event and checkpoint state between ChatGPT and the macOS CLI through Notion.
- Suppress replay for comments at or before the authoritative shared checkpoint.
- Verify target macOS CLI replay produced zero mutations, ignored records, or conflicts.
- Preserve v4.3.0 as the immediate immutable rollback baseline.

## 4.3.0 - 2026-07-21

- Promote W04 Todoist-to-Notion reconciliation after controlled production acceptance.
- Verified 28 planned changes applied and read back successfully: 9 Action Record updates and 19 Execution Step creations.
- Verified immediate full replay produced zero mutations, conflicts, ignored records, or writes.
- Preserve attended, review-first operating boundaries and v4.2.0 as the immediate immutable rollback.


## 4.3.0-rc.7 - 2026-07-21

- Create missing Notion Execution Step mappings during attended W04 reconciliation instead of reporting a nonexistent bootstrap command.
- Aggregate all conflict mutations into the top-level dry-run conflict list.
- Preserve readback verification for newly created Execution Step pages.



## 4.3.0-rc.6 — 2026-07-21

- Make `@atlas update` replay idempotent against live Notion state, even with a fresh local runtime database.
- Preserve local processed-event checkpoints as an optimization rather than the sole replay-safety mechanism.
- Add regression coverage for cross-install status-comment replay.


## 4.3.0-rc.5 — 2026-07-21

- Suppress unchanged Action Record and Execution Step mutations during reconciliation.
- Normalize Notion/Todoist datetime comparison to Notion minute precision.
- Add regression coverage proving zero-mutation replay after a successful apply.


## 4.3.0-rc.4 — 2026-07-21

- Accept the Todoist completed-task endpoint's `items` pagination envelope.
- Add regression coverage for completed-task response parsing.

## 4.3.0-rc.3 - 2026-07-21

- Use Notion API version `2025-09-03` for `/data_sources` query and create operations.
- Include Notion HTTP response bodies in adapter errors for actionable diagnostics.

## 4.2.0-rc.4

- Added a typed macOS Keychain credential boundary for the previously provisioned Notion and
  Todoist credentials.

## 4.2.0-rc.3

- Corrected candidate checksum inventory to exclude disposable local tool caches.
- Corrected restoration-package generator lint handling for embedded immutable document text.

## 4.2.0-rc.2

- Added typed live Notion and Todoist adapters, contract fakes, error translation, timeouts, and
  stable Todoist idempotency keys.
- Enabled confirmed W03 apply only when a configured adapter validates the live destination and
  reads back the task before storing linkage.
- Recorded controlled Notion/Todoist live acceptance evidence; no production release promotion.

## 4.2.0-rc.1

- First inactive Python candidate platform, preserving v4.1.0 production and v4.0.1 rollback unchanged.

## 4.3.0-rc.1

- Added attended W04 Todoist-to-Notion reconciliation.
- Added Todoist task metadata, comments, completed-task and child-task reads.
- Added Notion data-source query support.
- Added persistent reconciliation checkpoints and processed-comment idempotency.
- Added structured `@atlas` commands for updates, delegation, blockers, unblock, and checkpoints.
- Added conflict recording and readback verification.
- Added W04 schema migration and operating runbook.

## 4.4.1 - Candidate
- Added shared-checkpoint replay suppression for Todoist comments older than or equal to the authoritative Notion checkpoint.
- Added cross-surface tests proving older unledgered comments are suppressed while newer comments remain actionable.

- Added connector-native attended W04 reconciliation contract.
- Added shared Notion reconciliation-state store for CLI/ChatGPT replay suppression.
- Retained SQLite state as a recovery fallback.
- Added connector-native W04 runbook and cross-surface idempotency acceptance requirements.

## 5.0.0rc1 — Milestone 2

- Added Ryan Intelligence Evaluation Set v1.0 with 18 immutable core cases.
- Added documented-capability baseline for Atlas ROS v4.5.3.
- Added evaluation-set coverage and referential-integrity validation.
- Added `atlas intelligence validate-set` CLI command.
- Explicitly separated documented capability from live behavioral observation.

## 5.0.0rc1 — Milestone 3

- Added immutable Canonical Intelligence Record contracts for evidence, context, predictions, recommendations, decisions, and learning events.
- Added deterministic serialization, SHA-256 integrity validation, typed record references, append-only SQLite persistence, migration registry, generated schemas, and regression coverage.

## v5.0 development — Milestone 7
- Added governed outcome-linked learning and adaptation proposals.
- Added approval gates, bounded confidence updates, rollback-safe application, and longitudinal learning-quality evaluation.

## v5.0.0rc1 — Milestone 9

- Added governed candidate-preparation evidence packets.
- Added fixed mandatory gate completeness and failure checks.
- Added independent-review approval and changes-required controls.
- Added artifact SHA-256 verification and deterministic packet fingerprints.
- Added explicit separation between candidate proposal and promotion authority.
- Expanded regression coverage to 131 passing tests and 88.85% branch coverage.

## v5.0 Release Control Center
- Added a read-only control center generated from Release Validation Workbench evidence.
- Added gate, blocker, artifact-integrity, active/rollback authority, candidate-readiness, and promotion-boundary views.
- Added deterministic JSON and dashboard fingerprints.

## v5.0 promotion preparation
- Added Ryan Intelligence Evaluation Set v1 with 60 promotion cases.
- Added deterministic promotion-readiness evidence builder and blocking boundaries.
