# ADR-0083: Independent Production Reconciliation Ledger

## Decision

Atlas ROS v8.2.1 will replace the unusable historical W04 reconciliation target with one
independent Notion database named `Execution Reconciliation State`. Its data source is the
sole production deduplication ledger for both CLI and ChatGPT reconciliation.

The historical database `ba2518b1-3c97-4a94-8324-414f74ed8830` and data source
`afbb753c-3112-4784-9165-f786b503d1f7` remain deleted and prohibited. They are not a
migration source and are never restored, renamed, or written.

## Contract

The ledger has the version-neutral properties `State Key`, `State Type`, `Status`, `Cursor`,
`Event ID`, `Processed At`, `Execution Surface`, and `Notes`. Physical `Status` is restricted
to `Applied` and `Failed`; the versioned JSON evidence envelope in `Notes` holds logical state,
event aliases, provenance, authorization binding, digests, and readback outcome.

New comment records use the v8.2 canonical `todoist-comment:<comment-id>` identity and retain
`comment:<comment-id>` as an alias. A checkpoint is permitted only after every pre-cutover
source comment has a verified terminal baseline record.

## Safety controls

Production reconciliation fails closed when either identity is missing, W04 is selected, a
target is deleted or historical, the schema/options are incomplete, or the checkpoint is absent.
It cannot fall back to local SQLite. Baseline execution remains a separately authorized,
attended operation bound to an immutable cutover timestamp, source-inventory digest, plan digest,
and run identity.

## Rollback

Rollback preserves the new ledger, baseline evidence, and verified checkpoint. It must not
restore W04. If an older release cannot safely consume the replacement ledger, activation stops
until a validated rollback adapter is available.
