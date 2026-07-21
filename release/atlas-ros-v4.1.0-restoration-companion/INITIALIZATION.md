# Atlas ROS v4 Initialization

## Quick initialization
1. Read the Drive Release Index.
2. Confirm one Active release and immediate rollback.
3. Read the Notion System State.
4. Read the Active release manifest.
5. Read the Integration Inventory identified by the Active release manifest. Do not use a release-specific hard-coded collection ID.
6. Confirm published workspace validity and current operating limitations.

## Status
- READY: authorities agree and required integrations are current.
- READY WITH WARNINGS: authorities agree but a non-blocking production gap is recorded.
- INITIALIZATION BLOCKED: required authority is inaccessible, stale, or contradictory.

## Full validation
Use for release, recovery, audit, destructive migration, and consequential architecture changes. Validate all active schemas, registers, published files, checksums, and rollback integrity.
