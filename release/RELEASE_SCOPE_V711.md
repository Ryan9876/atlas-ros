# Atlas ROS v7.1.1 Corrective Release Scope

Status: Candidate implementation; not production authority.

## In scope

- One consolidated `quick_initialize` operation returning a typed compact receipt.
- Mandatory live `AUTHORITY.json` read on every attempt.
- Existing `WarmRuntimeCache` activated only for immutable Release Index and manifest material.
- Direct Integration Inventory data-source resolution from the governed manifest.
- Compact System State and Integration Inventory contracts.
- GitHub and Notion liveness inferred from successful required reads; one Todoist-only live probe.
- Per-stage monotonic timing and exact cold, warm, and warm-fallback path reporting.
- Minimal CI validation with no live provider calls, no matrix, one build, and short-lived diagnostics.

## Out of scope

- Release publication, tags, merges, or production authority activation.
- Production Notion System State or Integration Inventory writes.
- Connector permission or credential changes.
- Google Drive reads or retirement actions.
- Provider writes, autonomous scheduling, messaging, email, calendar, deletion, or live-network execution.
