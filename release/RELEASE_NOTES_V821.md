# Atlas ROS v8.2.1 Release Notes

v8.2.1 remediates the production reconciliation-state failure in v8.2.0.

- Creates and binds one new production `Execution Reconciliation State` ledger.
- Permanently rejects the deleted historical W04 database and data-source identities.
- Requires a complete, verified, digest-bound baseline checkpoint before activation.
- Preserves the exact cutover from the evidence envelope when Notion rounds display dates.
- Supports the connector's single extra JSON-string serialization layer without weakening envelope validation.
- Establishes a zero-event, zero-Todoist-write baseline across 31 mapped parent tasks and 89 subtasks.
- Adds complete full-candidate gates: security scan, dependency audits, clean installs, and v8.2.0/v8.1.0 restoration.

The release remains attended and review-first. It does not enable autonomous provider writes or expand integration scope.
