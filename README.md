# Atlas ROS Python Platform — Candidate v4.2.0-rc.5

An inactive, policy-driven candidate that preserves Drive as release authority, Notion as dynamic management authority, Todoist as execution authority, and SQLite as non-authoritative local runtime state.

## Safety

All write-capable commands default to dry-run. `atlas todoist apply` rejects execution unless explicitly confirmed and an adapter configured for writes is provided. This candidate contains no production credentials or embedded production IDs.

## Live adapters

The Notion and Todoist adapters are typed REST clients with explicit timeouts, redacted errors,
readback, and stable Todoist idempotency keys. They read credentials only from
`ATLAS_NOTION_TOKEN` and `ATLAS_TODOIST_TOKEN`; configure those through approved runtime credential
storage, never source control or SQLite. A confirmed W03 apply validates the live destination and
readback before recording a Notion linkage.

On macOS, `atlas connectivity --keychain` reads the two named Keychain entries for the current
user and performs only two read-only calls: Notion's current-integration identity and Todoist's
project list. It creates, changes, or deletes nothing.

## Commands

`atlas initialize`, `atlas status`, `atlas validate --full`, `atlas health --json`, `atlas capture`, `atlas route`, `atlas decompose`, `atlas todoist plan`, `atlas todoist validate`, `atlas todoist reconcile`, `atlas release inventory`, `atlas release checksums`, `atlas release verify`, `atlas release candidate`, `atlas release preflight`, and `atlas release restore-test`.

See `docs/operations/OPERATIONS_RUNBOOK.md` and `docs/migration/MIGRATION_PLAN.md`.
