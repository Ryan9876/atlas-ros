# v8.3.0 Automation Register Candidate

Status: validated-not-active proposal; no production Automation Register write authorized.

| Field | Value |
|---|---|
| Automation | Event-Driven Autonomous Reconciliation |
| Release | 8.3.0 candidate |
| Trigger | Authenticated Todoist/Notion webhook, bounded provider backstop, attended replay |
| Default mode | `MONITOR_ONLY`; kill switch on |
| Auto-apply scope | Exact `8.3.0-rc1` allowlist after separate production policy activation |
| Approval scope | Delegation, inference, shared/cross-person work, tombstones, limits, corrective writes |
| Block scope | Authority/W04/identity/field/security/destructive/governance/prohibited-domain conflicts |
| Owner | Ryan; production runtime owner pending |
| SLO | Accept ≤10s; start ≤60s after provider delivery; backstop convergence ≤15m |
| Evidence | Durable event, plan digest, policy result, mutations, readback, receipt, checkpoint |
| Kill switch | Separate auto-apply control; intake preserved |
| Activation prerequisites | Exact package promotion, runtime/secrets approval, webhook/OAuth setup, monitor-only proof, exact policy authorization |
