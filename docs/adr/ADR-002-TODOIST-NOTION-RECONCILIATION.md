# ADR-002: Todoist-to-Notion Reconciliation

## Status

Candidate for Atlas ROS v4.3.0.

## Decision

Introduce W04 as an attended reconciliation workflow with field-level authority, persistent idempotency state, structured `@atlas` comments, canonical provider readback, and explicit conflict records.

## Consequences

- Todoist remains an execution interface, not the management system of record.
- Notion receives fresher dates, completion, progress, delegation, blocker, and status data.
- New Action Record fields and an Execution Steps data source are required before production activation.
- Autonomous scheduling and webhook activation remain out of scope until separately accepted.
