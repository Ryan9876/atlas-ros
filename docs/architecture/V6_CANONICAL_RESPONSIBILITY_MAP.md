# v6 Canonical Responsibility Map

| Component | Owns | Must not own |
|---|---|---|
| Capture Service | durable capture envelope and outbox | classification or execution |
| Management Reasoning Engine | responsibility-first reasoning | provider access |
| Knowledge Composition Engine | governed knowledge modules | tasks |
| Management Structure Engine | management package | tasks |
| Record Routing Service | deterministic destination | provider writes |
| Execution Planner | task projection and economy | authorization or providers |
| Execution Orchestrator | exact-plan transaction | replanning |
| Todoist Adapter | Todoist operations and readback | task existence or field authority |
| Notion Adapter | Notion operations and readback | management policy |
| Execution Reconciliation Service | authority, conflict, idempotency, checkpoints, receipts | raw provider API behavior |

Dependency direction follows contracts → engines/planning → orchestration/reconciliation → ports →
adapters. Semantic capabilities never depend on retired numbered interfaces.
