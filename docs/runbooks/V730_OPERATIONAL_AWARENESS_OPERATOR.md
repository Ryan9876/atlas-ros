# v7.3 Operational Awareness Operator Runbook

Candidate-only guidance. Production v7.1.1 remains unchanged.

## On-demand commands

```text
atlas awareness brief --input SNAPSHOT.json --format human
atlas awareness context RECORD --input SNAPSHOT.json
atlas awareness resume RECORD --input SNAPSHOT.json
atlas awareness hygiene scan --input SNAPSHOT.json
atlas awareness hygiene propose FINDING --input SNAPSHOT.json
atlas lifecycle interpret --command-text TEXT --source-task-id ID --source-revision REV --snapshot SNAPSHOT.json
atlas lifecycle plan --command-text TEXT --source-task-id ID --source-revision REV --snapshot SNAPSHOT.json
```

All awareness commands are read-only. Lifecycle planning ends with an unexecuted `ProposedExecutionPlan`; provider writes require a separate immutable attended authorization. No recurring delivery, polling, webhook, email, message, calendar, or autonomous repair is enabled.

Stop when authority is missing, evidence is materially contradictory, parent resolution is ambiguous, the exact object budget is exceeded, or required readback cannot be defined.
