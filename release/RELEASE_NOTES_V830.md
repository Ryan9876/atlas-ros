# Atlas ROS v8.3.0

v8.3.0 introduces governed event-driven reconciliation contracts for Todoist
task/comment changes and authoritative Notion Universal Inbox captures.

The release adds authenticated webhook receivers, durable acceptance, event and
semantic deduplication, aggregate leases, retry/dead-letter recovery, bounded
backstops, feedback-loop verification, exact approval binding, Universal Inbox
task-creation limits, policy evaluation, and operator controls.

This is a software and governance release. Production event handling remains
inactive at release: `MONITOR_ONLY`, kill switch enabled, and ingress, planning,
auto-apply, approval, backstop, and replay disabled. Runtime, secrets, OAuth and
webhook setup, monitor-only parity, and a separate exact policy activation remain
required before autonomous reconciliation can perform business-provider writes.

The v8.2.1 reconciliation ledger and checkpoint remain authoritative and become
the immediate rollback. Both W04 identities remain permanently prohibited.
