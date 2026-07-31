# Atlas ROS v8.2.1 Exact Package and Production Authorization

Status: **template — not authorized**

This record must be completed only from independently read-back evidence.

- Exact source commit: `<COMMIT>`
- Retained candidate artifact and digest: `<ARTIFACT_ID>` / `<SHA256>`
- Source and wheel checksums: `<SDIST_SHA256>` / `<WHEEL_SHA256>`
- Active release / immediate rollback: `<ACTIVE>` / `<ROLLBACK>`
- New database / data-source / checkpoint identities: `<DATABASE_ID>` / `<DATA_SOURCE_ID>` / `<CHECKPOINT_ID>`
- Baseline cutover, inventory digest, and plan digest: `<UTC>` / `<DIGEST>` / `<DIGEST>`
- Baseline authorization identity and replay receipt: `<AUTHORIZATION>` / `<RECEIPT>`

Authorize separately and explicitly:

1. New production ledger creation and schema registration.
2. The exact baseline plan and checkpoint creation.
3. Publication of the exact retained package.
4. GitHub authority activation and matching Notion System State update.

No authorization may restore, rename, reconnect, read as a migration source, or write
to either historical W04 identity.
