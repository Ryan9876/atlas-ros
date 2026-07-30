# Atlas ROS v7.7.0 Candidate Release Notes

Atlas ROS v7.7.0 introduces a deterministic Initialization Circuit Breaker for ordinary Quick Initialization.

## Candidate changes

- Adds an explicit typed initialization state machine with irreversible terminal states.
- Adds an operation-scoped capability and exact-target allowlist before provider calls.
- Enforces the six-read clean cold path and four-read clean warm path.
- Adds one bounded transient retry with no retry for contradictions or integrity failures.
- Rejects duplicate, out-of-order, unauthorized-target, prohibited-capability, budget-excess, and post-terminal calls before provider invocation.
- Versions the initialization receipt to schema 2.0 while preserving accepted schema 1.0 fields.
- Adds deterministic trace, rejection, budget, cache, retry, and terminal-lock evidence.
- Keeps Quick Initialization separate from Full Validation.
- Keeps intent memory, the Ryan profile, communication policy, and playbooks outside Quick Initialization.

## Production state

This is a non-publishing candidate. Atlas ROS v7.6.1 remains Active. No production authority, schema, integration, Todoist, messaging, calendar, credential, deletion, scheduling, or network state is changed.
