# Atlas ROS v7.3 Responsibility Map

| Layer | Owns | Must not do |
|---|---|---|
| GitHub | Source, contracts, policy, schemas, release evidence, restoration | Represent live management state |
| Notion | Dynamic management state, delegation, evidence, decisions, risks | Become execution authority |
| Todoist | Persistent Ryan-owned outcomes and current checkpoints | Represent delegated implementation as Ryan work |
| SQLite | Cursors, watermarks, journals, caches, replay indexes | Become business authority |
| Operational Awareness | Evidence normalization, inference, briefs, context, hygiene proposals | Plan, authorize, write, reconcile |
| Command Lifecycle | Interpret explicit bounded intent and propose typed transitions | Invoke adapters or authorize |
| Canonical planner | Compile exact provider-neutral operations | Authorize or write |
| Attended authorization/execution | Bind and apply exact operations with readback | Expand intent |
| Reconciliation | Verify and close planned transactions | Create successor intent |

The Todoist projection invariant is: persistent parent outcome plus only the current independently actionable Ryan-owned checkpoint.
