# v4.5.0 Schema and Section Migration

## Todoist
Rename Operations & Follow-up to Operations. Rename Waiting / Follow-up to Waiting on Others. Reorder sections to the governed order. Preserve task IDs and task trees.

## Notion Execution Steps
Add Execution Priority select P1-P4 and Execution State select Ready, In Progress, Waiting, Blocked, Delegated, Review, Complete. Blank priority inherits the parent Action priority.

## Notion Risks and Blockers
Add Related Execution Step relation, Waiting On text, and Issue type. Use Todoist Command ID for idempotency.

## Rollback
Restore v4.4.2 package and revert live schema/section changes only through an explicitly authorized rollback plan. Historical release records remain immutable.
