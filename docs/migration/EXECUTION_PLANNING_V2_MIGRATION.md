# Execution Planning V2 Migration

## Scope

Atlas ROS v5.5 adds an additive planning boundary after `ManagementPackageV2`.
The migration does not change provider authorization, Todoist write controls,
record routing, rollback authority, or the W03/W03A aliases.

## Adoption sequence

1. Produce and validate a `ManagementPackageV2`.
2. Extract immutable `ExecutionCandidate` records with
   `ExecutionCandidateExtractor`.
3. Build an `ExistingRepresentationIndex` from provider-neutral readback.
4. Call `ExecutionPlanner.plan_v2` for one parent outcome, or
   `plan_many_v2` when independently valid parent outcomes are explicitly
   related to their child candidates.
5. Verify candidate, decision, and plan digests before downstream use.
6. Keep the resulting plan unauthorized. A separate governed boundary must
   authorize, execute, read back, and receipt any provider mutation.

## Compatibility

Existing W03A callers may continue using `ExecutionPlanner.plan` and
`ExecutionPlan` V1. A V2 plan may call `project_v1()` only when it has no
decomposition-review gate, no unresolved human decision, and a valid parent
outcome. Unsafe lossy projection raises `ValueError`.

## Operations and rollback

- Treat an ambiguous duplicate or representation match as review-required.
- Treat more than five eligible subtasks as a decomposition-review gate.
- Do not create tasks for future-horizon, completed, embedded, or non-Ryan-owned
  candidates.
- Verify `authorized` remains `false` before handing the plan to any downstream
  component.
- Roll back by selecting the unchanged v5.4 planner path and V1 compatibility
  surface; do not mutate stored provider objects as part of software rollback.

## Evidence

Run the full test suite, architecture validator, schema generator, and
`scripts/evaluate_execution_planning.py`. The release-blocking benchmark must
pass all fixtures and report zero provider writes and zero authorized execution
objects.
