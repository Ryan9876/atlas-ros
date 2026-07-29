# Atlas ROS v7.6.1 Definition of Done

The candidate is complete only when all conditions are true:

- Live authority proves v7.6.0 Active and v7.5.2 preserved lineage.
- One implementation branch and one draft PR contain the exact candidate.
- Feature contract, ADR, threat model, data map, and activation plan are present.
- Feature-disabled behavior is equivalent to v7.6.0.
- Required communication and decision playbooks pass targeted and full regression tests.
- Current instruction and live authority override profile behavior.
- High-consequence missing facts still require clarification.
- Privacy, prompt-injection, identity-isolation, determinism, and bounded-overhead tests pass.
- The production Ryan profile is absent from source, sdist, wheel, fixtures, workflow logs, and public metadata.
- Full lint, strict typing, architecture checks, tests and coverage, audits, clean installs, predecessor restoration, and nested checksums pass once on the frozen commit.
- Source and wheel are built exactly once and retained.
- A separate minimized Ryan profile bundle is validated, identity-bound, state-bound, digested, and read back outside the package workflow.
- One exact authorization block identifies the package and optional profile activation transaction.
- No publication, merge, production authority change, profile activation, schema mutation, Todoist task, message, calendar action, schedule, credential action, integration change, deletion, forgetting execution, or live-network action occurs before exact authorization.
