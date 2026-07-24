# Atlas ROS Remaining Roadmap Phase 1 — Classification Intelligence Execution Plan

Status: Approved execution plan for governed development. This plan does not promote or activate a production release.

Program target: Atlas ROS v6.0.0 final roadmap completion.

Current production authority: Atlas ROS v5.2.0.

Immediate immutable rollback: Atlas ROS v5.1.1.

Primary records: ATI-1, IDEA-1, IDEA-2, IDEA-3, V4D-18, and the continuing-development authorization recorded with this plan.

## 1. Purpose

Implement the first remaining Atlas ROS roadmap phase: **Classification Intelligence**.

For remaining-roadmap planning, this program is called **Phase 1**. It maps directly to the existing roadmap's **Wave 2 — Classification Intelligence Evolution** and preserves the existing internal sequence:

- Phase 1A / roadmap Phase 2A — Responsibility-first classification.
- Phase 1B / roadmap Phase 2B — Classification explainability.
- Phase 1C / roadmap Phase 2C — Manager intent inference.
- Phase 1D — Controlled cutover, release evidence, and compatibility validation.

The phase converts the Management Reasoning Engine from a wrapper around an externally proposed route into the governed owner of responsibility-aware classification intelligence, while keeping deterministic record routing, provider adapters, and consequential writes outside the engine.

## 2. Authorization and decision rights

The delegated development authority granted to Atlas for the v5.2 development program applies continuously to this phase and to all future approved Atlas ROS development.

Atlas may make and implement development-scope decisions without recommendation-by-recommendation approval, including:

- architecture and component boundaries;
- internal contracts and additive schema evolution;
- implementation sequence and development milestones;
- algorithms, deterministic rules, confidence methods, and fallback behavior;
- refactoring, simplification, reliability, performance, observability, security, testability, and maintainability improvements;
- test strategy, fixtures, evaluation datasets, calibration methods, and quality thresholds that meet or exceed governed minimums;
- development branches, commits, pull requests, ADRs, migration plans, release tooling, documentation, implementation-registry updates, and candidate packaging;
- material improvements discovered during implementation when they remain within the approved program purpose and operating boundaries.

Ryan remains the sole authority for:

- release promotion and production activation;
- destructive or irreversible production migrations;
- deletion or mutation of historical authority records or immutable release artifacts;
- new external integrations or expanded integration permissions;
- activation of autonomous scheduling, messaging, email, calendar, deletion, or unattended consequential automation;
- waiver of required quality, security, integrity, restoration, reconciliation, publication, or rollback evidence;
- changes to Ryan's sole-reviewer or sole-promotion authority.

Atlas must escalate only when a decision crosses one of those reserved boundaries, materially expands the approved program, creates a new financial or external commitment, or cannot satisfy a blocking validation gate.

## 3. Current baseline

The v5.2 architecture provides the structural foundation but not the target intelligence:

- `ManagementReasoningEngine` is provider-independent, but it currently receives an existing `RoutingRecommendation` and restates its classification and destination.
- `RecordRoutingService` validates allowed classifications, validates the classification-to-destination mapping, and fails closed on low confidence, ambiguity, or required human review.
- `RoutingService` remains a W02 compatibility facade over the LLM adapter, Management Reasoning Engine, and Record Routing Service.
- `ReasoningPackage` version 1 contains classification, destination, confidence, rationale, ambiguities, and a human-decision flag, but it does not represent responsibility domain, workstream, operating context, decisive evidence, challenge state, or fallback reason.
- `config/classifications.yaml` governs record types and destination databases but does not define responsibility domains or manager operating contexts.
- The current test suite proves provider separation, fail-closed routing, invalid-destination rejection, compatibility equivalence, and shadow-drift detection.

This phase must extend those controls rather than replace or bypass them.

## 4. Scope

### In scope

- Responsibility-first classification using `Responsibility -> Outcome -> Workstream -> Activity`.
- Separation of record type, responsibility domain, management workstream, activity, and provider destination.
- Concise classification explanations based on decisive evidence.
- Manager operating-context inference as an additional governed signal.
- Confidence calibration, ambiguity handling, challenge support, and safe fallback.
- Shadow comparison against the current W02 path.
- Compatibility facades and additive migration contracts.
- Dedicated evaluation fixtures for leadership-versus-technical ambiguity.
- Observability, audit evidence, implementation-registry reconciliation, release validation, and rollback proof.

### Out of scope

- Provider write authorization inside the reasoning engine.
- Todoist or Notion adapter redesign beyond compatibility changes required to carry the new reasoning metadata.
- Knowledge Composition Engine or Management Structure Engine implementation.
- Execution Planner, task-economy, or execution-orchestration changes.
- New external integrations or permission expansion.
- Autonomous or unattended consequential operation.
- W-number interface retirement.

## 5. Target architecture

### 5.1 Classification dimensions

The engine must model these dimensions independently:

1. **Record classification** — action, project, delegated work, risk, decision, reference, or needs clarification.
2. **Responsibility domain** — why Ryan owns the work.
3. **Desired outcome** — the governed result Ryan is accountable for.
4. **Management workstream** — where the responsibility belongs operationally.
5. **Activity** — the concrete work or event described by the capture.
6. **Operating context** — the managerial role Ryan is performing, when supported by evidence.
7. **Destination** — the authoritative record store selected by deterministic routing policy.

The engine must never infer that a technical activity belongs to Operations solely because the activity is technical. It must first determine why Ryan owns the outcome.

### 5.2 Responsibility domains

The initial governed taxonomy is:

- People Leadership -> Leadership & Team.
- Project Delivery -> Active Projects.
- Operational Stewardship -> Operations.
- External Dependency -> Waiting on Others.
- Capability Building -> Development & Learning.

Record classification remains separate. For example, a People Leadership responsibility may still produce an Action Record, Delegated Work record, Decision record, or Risk record depending on the object being represented.

### 5.3 Operating contexts

The initial operating-context taxonomy is:

- People Leader.
- Project Manager.
- Operations Manager.
- Strategic Planner.
- Individual Contributor.
- Executive.

Operating context is supporting evidence only. It may adjust confidence or resolve otherwise-close alternatives, but it may not override explicit ownership, authority, safety, project, risk, or decision evidence.

### 5.4 Contract evolution

Implement an additive versioned reasoning contract rather than silently changing version 1 semantics.

The new contract must represent at least:

- record classification;
- responsibility domain;
- desired outcome;
- workstream;
- activity summary;
- operating context and context confidence when present;
- overall confidence;
- decisive evidence signals;
- concise user-facing rationale;
- ambiguities and challenged state;
- fallback or clarification reason;
- compatibility classification and destination.

Version 1 consumers must continue to operate through an explicit compatibility projection until the later canonical-cutover phase.

### 5.5 Component boundaries

- **Management Reasoning Engine:** generates responsibility-aware reasoning and confidence evidence.
- **Classification Explainability component:** converts decisive evidence into a concise governed rationale; it does not expose hidden chain-of-thought or unnecessary internal processing.
- **Manager Intent component:** infers operating context with confidence and evidence; it cannot decide destination independently.
- **Record Routing Service:** remains the deterministic authority for validating record classification and destination.
- **Routing Shadow Comparator:** compares legacy and semantic outputs at field level and records material drift.
- **Provider adapters:** remain limited to provider-specific reads and writes and cannot classify work.

Architectural fitness tests must prevent engines from importing Todoist, Notion, Google Drive, or other provider adapters.

## 6. Execution sequence

## Gate 0 — Program baseline and traceability

### Deliverables

- Create an ADR for responsibility-first classification, explainability, intent inference, compatibility, and fallback behavior.
- Freeze the current v5.2 classification and routing baseline.
- Version a dedicated responsibility-classification evaluation set.
- Map every requirement to ATI-1, IDEA-1, IDEA-2, or IDEA-3.
- Add the phase to the machine-readable implementation registry.
- Extend the shadow-comparison evidence model to include responsibility domain, workstream, confidence, rationale category, and fallback.
- Define privacy and evidence-minimization rules for explanations and intent signals.

### Exit gate

- Existing v5.2 tests pass unchanged.
- Baseline metrics and known ambiguity classes are published.
- Contract and migration designs are reviewable and rollback-safe.
- No production behavior has changed.

## Phase 1A — Responsibility-first classification

### Deliverables

- Add governed responsibility-domain and workstream taxonomies.
- Add versioned reasoning-contract models and compatibility projection.
- Implement responsibility-signal extraction from capture content and supplied context.
- Implement deterministic precedence rules for explicit people, project, operations, dependency, development, decision, risk, and ownership evidence.
- Implement responsibility scoring and confidence calculation.
- Produce desired outcome, workstream, and activity independently from provider destination.
- Add deterministic fixtures for ambiguous cases, including:
  - enabling a direct report through technical access work;
  - resolving a production incident owned as operational stewardship;
  - coordinating technical implementation owned as project delivery;
  - waiting on a vendor or another team;
  - training, certification, or capability development;
  - delegated technical execution where Ryan retains management accountability.
- Run semantic classification in shadow mode against the current W02 path.

### Exit gate

- Critical responsibility fixtures pass at 100%.
- Record-type and destination behavior remains equivalent on non-target regression cases.
- People-leadership versus technical-activity cases meet the approved quantitative threshold.
- Low-confidence or conflicting evidence fails safely to clarification or the documented compatibility fallback.
- No provider writes or integration-scope changes occur.

## Phase 1B — Classification explainability

### Deliverables

- Generate one concise explanation identifying the primary responsibility and selected workstream.
- Record the decisive signal category and evidence references in the versioned Reasoning Package.
- Distinguish user-facing explanation from internal evaluation diagnostics.
- Add challenge metadata so a routing decision can be marked accepted, challenged, corrected, or unresolved without mutating historical evidence.
- Add explanation-quality fixtures for accuracy, concision, non-deceptiveness, and evidence alignment.
- Add observability for low-confidence, challenged, corrected, and fallback classifications.

### Explanation contract

A valid explanation must:

- state the selected responsibility or workstream;
- identify the decisive evidence in plain language;
- avoid unsupported certainty;
- disclose ambiguity when it materially affects the result;
- avoid exposing unnecessary internal reasoning;
- remain stable enough for audit and tuning.

### Exit gate

- Every semantic classification produces a valid concise explanation.
- Explanation text agrees with the structured decisive evidence.
- Challenge and correction events are traceable and idempotent.
- Explanations do not disclose secrets, hidden internal reasoning, or unrelated personal context.

## Phase 1C — Manager intent inference

### Deliverables

- Implement the governed operating-context taxonomy.
- Extract intent signals from explicit capture context, current governed management context, and approved contextual records.
- Assign independent context confidence and evidence.
- Prevent intent from becoming sole classification authority.
- Add conflict handling when intent evidence disagrees with explicit responsibility, project, operational, risk, or authority evidence.
- Run intent inference in shadow mode until Phase 1A and 1B are stable.
- Add adversarial and sparse-context fixtures.

### Exit gate

- Intent inference never overrides stronger explicit evidence.
- Low-confidence intent is omitted or surfaced as uncertain rather than silently applied.
- Responsibility classification remains explainable with or without intent.
- Shadow evidence shows measurable improvement on approved ambiguous cases without material regression elsewhere.

## Phase 1D — Controlled cutover and candidate preparation

### Rollout stages

1. **Shadow only:** semantic decisions are computed and compared but cannot change routing.
2. **Attended decision support:** semantic decision and explanation are shown during approved processing; the legacy route remains the compatibility authority.
3. **High-confidence canonical mode:** the semantic decision becomes canonical only for validated high-confidence classes; all other cases use clarification or a documented compatibility fallback.
4. **Compatibility release candidate:** package the capability with v1 projection, migration evidence, rollback proof, and full release validation.

No stage may activate unattended consequential processing.

### Exit gate

- Management Reasoning Engine owns classification intelligence.
- Record Routing Service remains the deterministic destination authority.
- Provider adapters remain classification-free.
- Current attended and review-first boundaries are preserved.
- Production readback, restoration, rollback, implementation-registry, Decision Log, Review Record, Automation Register, Integration Inventory, and release-manifest evidence agree.
- Ryan explicitly authorizes any production promotion.

## 7. Engineering work products

### Source and contracts

Expected source changes include:

- versioned reasoning contracts;
- responsibility and operating-context domain models;
- responsibility classifier and signal model;
- explainability builder;
- manager-intent inference component;
- confidence and fallback policy;
- extended shadow comparator;
- compatibility projection for W02 and version 1 consumers;
- observability events and structured evaluation output.

Exact module names may change under Atlas's delegated architecture authority when a simpler or safer design is identified.

### Configuration

Add governed versioned configuration for:

- responsibility domains and workstream mapping;
- evidence precedence;
- confidence thresholds;
- ambiguity and conflict policy;
- intent contexts;
- high-confidence canonical-mode allowlist;
- explanation limits and redaction rules.

Configuration must be schema-validated and fail closed.

### Documentation

- Architecture Decision Record.
- Contract reference and compatibility guide.
- Classification taxonomy and evidence standard.
- Explainability standard.
- Manager-intent governance standard.
- Migration and rollback plan.
- Operator and troubleshooting runbook.
- Evaluation and calibration report.
- Release scope, implementation registry, changelog, and candidate evidence.

## 8. Test and validation strategy

### Mandatory regression gates

- All existing v5.2 regression tests pass.
- Ruff and strict MyPy pass.
- Branch coverage remains at or above the governed 85% minimum and does not materially decline from the v5.2 baseline without a documented accepted reason.
- Source distribution, wheel build, clean-wheel install, source manifest, extracted-source verification, SBOM, dependency policy, dual advisory audits, and package checksums pass.
- Architectural tests prove reasoning components cannot import provider adapters.
- Restoration-companion and rollback checksums pass.

### Classification evaluation gates

The dedicated evaluation report must include:

- confusion matrix by record classification and responsibility domain;
- macro precision, recall, and F1;
- per-domain recall;
- people-leadership versus operations ambiguity performance;
- low-confidence and clarification precision;
- confidence calibration;
- explanation-evidence agreement;
- legacy-versus-semantic differential results;
- challenged and corrected case analysis.

Minimum candidate thresholds:

- 100% pass on blocking safety, authority, explicit-decision, explicit-risk, and critical responsibility fixtures.
- Macro F1 of at least 0.90 for responsibility domain on the frozen held-out set.
- Recall of at least 0.85 for every responsibility domain.
- At least 0.99 equivalence on record classification and destination for non-target legacy regression cases.
- Confidence calibration error no greater than 0.10 on the held-out set.
- At least 0.95 structured agreement between explanation and decisive evidence.

Atlas may raise these thresholds based on baseline results. Lowering a blocking threshold requires Ryan's explicit authorization because it waives a quality gate.

## 9. Data and evaluation controls

- Use synthetic, de-identified, or already-authorized governed examples whenever possible.
- Do not copy secrets, credentials, private messages, or unnecessary personal data into fixtures.
- Separate training/tuning cases from held-out acceptance cases.
- Version every dataset and record its checksum.
- Record the source category and authorization basis for each non-synthetic fixture.
- Preserve failed and challenged examples for regression testing without exposing unnecessary sensitive content.
- Do not infer durable personal preferences or authority from a single ambiguous example.

## 10. Compatibility, migration, and rollback

- Preserve the W02 compatibility facade throughout this phase.
- Keep version 1 Reasoning Package projection until a later canonical-cutover release retires it.
- Make new fields additive and schema-versioned.
- Do not destructively rewrite historical reasoning or routing evidence.
- Run legacy and semantic paths in parallel before canonical cutover.
- Store field-level differential evidence for every shadow case.
- Provide a feature-controlled fallback to the v5.2 classification path.
- Prove that rollback restores the prior Active package and leaves Notion, Todoist, and historical evidence consistent.
- Do not update the Release Index or System State until an explicitly authorized promotion transaction.

## 11. Observability and operating controls

Track at least:

- classification count by record type, responsibility domain, workstream, and operating context;
- confidence distribution;
- clarification and fallback rate;
- shadow disagreement rate and material-drift fields;
- challenged and corrected decisions;
- explanation generation failures;
- processing latency and error class;
- compatibility projection failures;
- provider-boundary violations detected by tests.

No classification metric may trigger an autonomous provider write or production policy change.

## 12. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Technical wording overwhelms managerial responsibility | Responsibility precedence and dedicated people-versus-operations fixtures |
| Intent inference creates false confidence | Independent confidence, supporting-signal-only rule, safe omission, and shadow validation |
| Record type and workstream become conflated | Separate contract fields and deterministic routing authority |
| Explanations expose unnecessary internal reasoning | Structured decisive evidence plus concise explanation builder and redaction rules |
| New contract breaks v1 consumers | Versioned contract and explicit compatibility projection |
| Accuracy improves in one domain but regresses elsewhere | Frozen held-out set, per-domain gates, differential testing, and rollback |
| Classification changes silently increase tasks | No execution planning in scope; task creation remains governed by existing W03 and future Execution Planner controls |
| Development authority is mistaken for production authority | Explicit reserved-decision boundary and Ryan-only promotion gate |

## 13. Release and governance strategy

This plan does not assign a release number to the Classification Intelligence compatibility release. Version selection occurs during governed candidate preparation. Atlas ROS v6.0.0 remains the designated final release for completion of the entire roadmap.

Every candidate produced from this phase must include:

- ATI-1 and IDEA-1/2/3 implementation dispositions;
- implemented and remaining scope;
- source commit and artifact digest;
- ADRs and contract versions;
- evaluation dataset and checksum;
- quantitative evaluation and calibration report;
- complete tests and security evidence;
- migration, compatibility, and rollback proof;
- implementation-registry reconciliation;
- Notion development-record reconciliation;
- publication and readback evidence;
- governed Review Record;
- Ryan's explicit production-promotion decision.

## 14. Phase completion criteria

Classification Intelligence is complete when:

1. Responsibility-first classification is canonical within the Management Reasoning Engine.
2. Every classification has structured decisive evidence and a concise governed explanation.
3. Manager intent is available as a confidence-scored supporting signal and cannot override stronger evidence.
4. Record classification, responsibility domain, workstream, activity, operating context, and destination are represented separately.
5. Low-confidence and conflicting cases fail safely.
6. Existing record routing, Todoist content, section routing, hierarchy, readback, duplicate prevention, attended execution, and rollback controls do not regress.
7. Compatibility and restoration are proven.
8. GitHub, Notion, implementation registry, release evidence, and production state agree.
9. A governed candidate passes Full Validation.
10. Ryan explicitly authorizes production promotion.

## 15. Immediate next development action

Create the dedicated development branch and implement Gate 0: ADR, versioned contract design, responsibility taxonomy, frozen evaluation baseline, implementation-registry entry, and expanded shadow-comparison evidence. No production activation or Todoist task creation is authorized by this planning document.