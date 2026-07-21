# W04 Production Schema Migration

This migration is required before W04 can be activated. It must be applied to a release candidate, read back, acceptance-tested, and promoted as a material schema/workflow release.

## Action Records additions

```sql
ADD COLUMN "Execution Due Date" DATE;
ADD COLUMN "Execution Priority" SELECT('P1':red, 'P2':orange, 'P3':yellow, 'P4':green);
ADD COLUMN "Latest Update" RICH_TEXT;
ADD COLUMN "Latest Update At" DATE;
ADD COLUMN "Todoist Updated At" DATE;
ADD COLUMN "Last Sync Source" SELECT('Todoist':red, 'Notion':blue, 'System':gray);
ADD COLUMN "Execution Steps" RELATION('<EXECUTION_STEPS_DATA_SOURCE_ID>', DUAL 'Parent Action');
ADD COLUMN "Execution Steps Total" ROLLUP('Execution Steps', 'Step', 'count_all');
ADD COLUMN "Execution Steps Completed" ROLLUP('Execution Steps', 'Completed', 'count_checked');
```

## Execution Steps data source

```sql
CREATE TABLE (
  "Step" TITLE,
  "Parent Action" RELATION('<ACTION_RECORDS_DATA_SOURCE_ID>', DUAL 'Execution Steps'),
  "Todoist Task ID" RICH_TEXT,
  "Todoist Task URL" URL,
  "Sequence" NUMBER,
  "Status" SELECT('Open':blue, 'Completed':green, 'Cancelled':gray),
  "Completed" CHECKBOX,
  "Due Date" DATE,
  "Completed At" DATE,
  "Latest Update" RICH_TEXT,
  "Last Verified" DATE,
  "Sync State" SELECT('Pending':yellow, 'Synced':green, 'Error':red),
  "Sync Error" RICH_TEXT
)
```

## Delegated Work additions

```sql
ADD COLUMN "Todoist Command ID" RICH_TEXT;
ADD COLUMN "Todoist Parent Task ID" RICH_TEXT;
```

## Risks and Blockers additions

```sql
ADD COLUMN "Todoist Command ID" RICH_TEXT;
ADD COLUMN "Todoist Parent Task ID" RICH_TEXT;
```

## Activation gates

- Dry-run produces correct mutations for a controlled mapped task.
- Due date and priority update only execution fields.
- Parent completion and reopen update Action status correctly.
- Each subtask maps to exactly one Execution Step.
- `@atlas update`, `delegate`, `blocker`, `unblock`, and `checkpoint` pass readback tests.
- Replayed comments do not duplicate records.
- Conflicts create ROS Operations records and do not overwrite Notion authority.
- Full validation and explicit promotion are complete.
