# Atlas ROS v8.2.0 Schema and Migration Assessment

Status: **validated design; no production Notion schema migration required**

## Live schema readback

The live configured reconciliation state data source exposes only these writable business properties:

- State Key
- State Type
- Status
- Cursor
- Event ID
- Processed At
- Execution Surface
- Notes

Its select contracts are fixed: `State Type` accepts `Checkpoint` or `Processed Event`; physical `Status` accepts `Applied` or `Failed`; `Execution Surface` accepts `CLI` or `ChatGPT`.

## Decision

Atlas ROS v8.2.0 preserves the complete typed reconciliation-event envelope without adding Notion properties:

1. The stable event identity remains in `State Key` and `Event ID`.
2. Persistence success/failure remains in physical `Status`.
3. The complete deterministic JSON event envelope is stored in `Notes`.
4. The envelope contains event type, provider, task/comment IDs, posted timestamp, source digest, interpretation classification and logical state, confidence, blockers, command and plan digests, authorization identity, processing outcome, processed timestamp, and originating execution surface.
5. Reads prefer the logical status in the versioned `Notes` envelope and retain compatibility with pre-v8.2 rows that expose only physical `Status`.
6. Local SQLite reconciliation state receives additive columns for the same typed fields through the existing runtime initialization migration.

## Production effect

- Notion data sources created: **0**
- Notion properties added, renamed, or removed: **0**
- Existing Notion records rewritten by migration: **0**
- Destructive schema operations: **0**
- Todoist writes during migration: **0**
- Production migration application required: **no**

## Compatibility and rollback

The representation is compatible with v8.1.0 and v8.0.0 because those releases already understand the existing top-level state properties and ignore the structured JSON stored in `Notes`. Rollback requires no reverse schema operation. New event rows remain durable evidence and are readable at their physical Applied/Failed level by older releases.
