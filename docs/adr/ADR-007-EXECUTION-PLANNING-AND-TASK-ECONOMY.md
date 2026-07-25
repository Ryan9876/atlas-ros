# ADR-007: Execution Planning and Task Economy

Status: Accepted for the Atlas ROS v5.5.0 candidate. Production activation remains Ryan-only.

## Context

Atlas ROS v5.4 provides a minimal provider-independent planner, but its V1 contract cannot
represent why every management item was or was not projected, progressive horizon state, layered
duplicate evidence, an existing-representation index, or governed decomposition review. Richer
Planning Models and Knowledge Modules must not create corresponding growth in external task
count.

## Decision

The canonical flow is:

`Management Package V2 → candidate extraction → Task Projection Test → duplicate and existing
representation analysis → progressive horizon → task budget → Execution Plan V2 → STOP`.

The Execution Planner is the exclusive component permitted to propose canonical execution
objects. It does not authorize, transact, call an adapter, produce a receipt, or claim provider
readback. Every Execution Plan V2 has `authorized=false`.

### Contracts

- `ExecutionCandidate` is immutable, provenance-bound, and digest-bound.
- `ProjectionDecision` records the result of all 14 Task Projection Test conditions.
- `ExistingRepresentationIndex` is a provider-neutral caller-supplied snapshot.
- `ExecutionPlanV2` records parent, projected steps, withheld candidates, duplicate and
  representation findings, horizon summary, task-budget decision, human-review requirements,
  policy version, and a deterministic digest.
- V1 contracts and W03A readers remain available. Lossy V2-to-V1 projections fail closed.

### Extraction

Extraction reads generic `execution_candidates` metadata from Management Package V2 sections.
It never branches on Team Operating Model, project, incident, SOP, or other artifact types.
Sections, Knowledge Modules, governance rules, approvals, decisions, evidence requirements, and
reference material remain management content unless an item independently passes the complete
projection test.

### Task Projection Test

Projection requires Ryan ownership, a concrete independently executable action, readiness,
specific observable Done When evidence, future attention, current horizon, resolved
prerequisites, incomplete state, no duplicate, no equivalent existing representation, inability
to remain embedded, material execution value, minimal-path fit, and provider-independent
validity. Every failed condition is structured and explained.

### Progressive horizon

Only `current` items are automatically proposed. `next`, `conditional`, and `future` remain
deferred; `blocked` remains a blocker unless a separate Ryan-owned unblock action qualifies;
`completed` never projects. Conditional and blocked candidates transition deterministically
when their trigger or prerequisites become true.

### Duplicate and representation policy

Duplicate layers are evaluated in deterministic order: candidate ID, normalized title,
normalized objective/Done When, canonical execution signature, source reference,
parent-child equivalence, and dependency equivalence. Ambiguous cases require review rather than
silent merging. Equivalent open representations suppress projection. Equivalent completed work
suppresses projection unless recurrence is explicit.

### Task budget

The default plan is one parent and zero to three meaningful subtasks. Four or five require every
subtask to be current, ready, independently executable, distinct, observable, and valuable, with
an explicit rationale. More than five withholds automatic subtask projection and produces a
decomposition-review requirement plus compression alternatives. The threshold cannot be used to
hide legitimate independent outcomes under a vague umbrella.

## Compatibility

W03A remains a temporary facade over the canonical planner. Its historical pattern selection and
expanded compatibility budget remain isolated in the facade. The semantic V2 entrypoint uses the
governed v5.5 policy. Objective and Done When rendering, section routing, hierarchy, attended
authorization, provider readback, and reconciliation remain downstream contracts.

## Determinism and failure semantics

Canonical ordering and normalized payloads bind candidate, decision, candidate-set, and plan
digests. Invalid package or candidate digests fail closed. Review-gated plans cannot contain
ordinary projected subtasks. Plans are safe to serialize and inspect without side effects.

## Release and rollback

The v5.5 candidate is additive to v5.4. V1 readers, W aliases, and provider boundaries remain
unchanged. Promotion requires exact-candidate CI, security, packaging, checksum, draft
publication/readback, Drive-independent restoration, Full Validation, and Ryan’s explicit
authorization. If promoted, v5.4 becomes the immediate immutable rollback.

