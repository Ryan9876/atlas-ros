# Atlas ROS Execution Planning Standard

Version: `execution-planning-v2.0.0`

## Responsibility boundary

The Execution Planner alone decides whether provider-neutral execution objects should be
proposed. The Management Reasoning Engine reasons, the Knowledge Composition Engine composes,
and the Management Structure Engine constructs artifacts. The Execution Orchestrator owns
attended authorization and transaction state. Provider adapters only perform provider-specific
operations. Reconciliation begins only after verified application.

Planning is not authorization. A plan must stop before orchestration and must always serialize
with `authorized=false`.

## Required input

The canonical input is a checksum-valid Management Package V2 plus an optional checksum-valid
provider-neutral Existing Representation Index. Callers may supply explicit candidates for
testing or governed integrations, but every candidate must use the same immutable V2 contract
and pass digest verification.

Management sections may expose generic `execution_candidates` metadata. No extractor may branch
on a specific Planning Model or artifact type.

## Candidate requirements

Each candidate carries stable identity, correlation, source package, type, objective, Done When,
owner, domain, workstream, section and item provenance, dependencies, trigger, completion and
readiness state, earliest horizon, representation hints, confidence, assumptions, ambiguities,
evidence, embeddability, execution-value signals, and a deterministic digest.

Only parent outcomes, independently executable actions, and qualifying risk responses may become
execution objects. Decisions, approvals, evidence, governance, dependencies, checklist detail,
conditional future work, and reference information remain management content by default.

## Task Projection Test

All 14 checks are release blocking:

1. Ryan ownership
2. Concrete independently executable action
3. Execution readiness
4. Specific binary Done When
5. Future attention
6. Current horizon
7. No unresolved prerequisite
8. Not already complete
9. Not a duplicate
10. Not already represented
11. Cannot remain embedded
12. Material execution value
13. Minimal-path task-economy fit
14. Provider-independent validity

Every candidate receives a Projection Decision with per-condition results and reason codes.

## Horizon policy

- `current`: eligible for projection
- `next`: retained until it becomes necessary for the current path
- `conditional`: retained until its trigger is true
- `future`: retained and uncreated
- `blocked`: retained as a blocker unless a separate unblock action qualifies
- `completed`: never projected
- `not_applicable`: retained as management context

Replanning may transition `conditional`, `blocked`, or `next` to `current` only from explicit
trigger or prerequisite evidence.

## Duplicate and existing-representation policy

Exact identity and deterministic equivalence suppress projection. Related-but-non-equivalent
work remains separate. Multiple equivalent matches are ambiguous and require review. Completed
representations suppress non-recurring work; recurrence must be explicit.

The planner never queries Todoist. A read layer supplies the provider-neutral index.

## Task budget

- Default: one parent and zero to three subtasks.
- Four or five: allowed only with a recorded rationale and full per-step qualification.
- More than five: automatic subtasks are withheld; a decomposition review, alternatives, and
  possible multiple-parent analysis are required.

Numeric compression must not erase legitimate independent outcomes.

## Done When quality

Every parent and subtask requires an observable, task-specific completion condition. Generic
statements such as “the work is done” fail the projection test. The canonical contract remains
provider neutral. The Todoist Adapter continues to render exact `**Objective:**` and
`**Done when:**` labels downstream.

## Observability

Events use IDs, digests, policy version, domain, workstream, status, and reason codes. They do not
log objectives, Done When text, or confidential management content. Required events cover
extraction, projection-test outcomes, duplicates, representations, horizon assignment,
deferral, selection, task budget, review requirements, plan generation or withholding,
compatibility projection, and authorization-boundary enforcement.

## Failure semantics

Invalid digests, unsupported enum states, ambiguous provider-neutral matches, unsafe V1
projections, noncontiguous sequences, review-gated projected steps, or any attempted planner
authorization fail closed. Planner evaluation has no provider side effect.

