# Atlas ROS v6.1.1 Security and Autonomy Boundary

Atlas ROS v6.1.1 changes provider-independent reasoning and validation only.

Unchanged boundaries:

- Google Drive and Notion remain required authorities.
- Todoist remains attended execution only.
- Calendar and email remain inactive.
- Outlook Email and Outlook Calendar remain prohibited.
- No autonomous scheduling, messaging, deletion, or consequential provider mutation is added.
- Adapters cannot plan or authorize.
- Orchestration cannot add work or reinterpret intent.
- Reconciliation cannot create unplanned execution work.
- Every external write still requires exact attended authorization, idempotency, readback, and fail-closed evidence.

Reasoning coherence executes before orchestration and performs zero provider writes.
