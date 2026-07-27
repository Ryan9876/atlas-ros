# Atlas ROS v6.5.0 Release Notes

## Summary

v6.5 adds governed execution intelligence as five separated provider-free capabilities. It improves the ability to compose policies, identify the minimum sufficient path, describe execution state, present evidence safely, and compare scenarios without gaining operational authority.

## What changed

- Framework composition applies deterministic precedence, provenance, policy conflict detection, and fail-closed dependency checks.
- Minimum effective path planning preserves mandatory controls, ordered prerequisites, rollback and escalation information.
- Execution intelligence models evidence, idempotency, retry, partial failure, readback completion, and next valid actions without provider writes.
- Human-readable presentation separates facts, assumptions, warnings, blockers, decisions, and next steps while redacting sensitive values.
- Scenario intelligence compares immutable, provider-neutral snapshots with explicit uncertainty, trade-offs, reversibility, and decision triggers.

## Security and governance

No integration scope, Todoist behavior, scheduling, messaging, email, deletion, live network execution, autonomous action, or provider-write capability is added. Generic frameworks never imply organizational adoption. Presentation and scenario analysis remain advisory and digest-bound.

## Compatibility

v6.5 is additive. Existing v6.2 behavior remains unchanged unless a caller explicitly uses the new public contracts and engines. The promotion package retains immutable v6.2.0 and v6.1.1 restoration checks.
