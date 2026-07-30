# Atlas ROS v8.1.0 Clarification Operator and Recovery Runbook

Status: candidate runbook; v8.1.0 is not production-active.

## Normal attended operation

1. Preserve the original capture, capture ID, and correlation ID.
2. Supply only bounded authoritative context relevant to the item.
3. Run context-aware analysis before downstream routing.
4. When clarification is required, store the analysis digest and mark only that item paused.
5. Surface the generated question at the next safe user-visible interruption, before processing the next item.
6. Leave later unrelated items eligible to continue after the interruption.
7. Do not create Notion destination records or Todoist tasks for the paused item.
8. Bind the user answer to the exact item and analysis digest.
9. Preserve the original capture and record the normalized instruction separately.
10. Re-run analysis and classification. A second focused question may be required when the corrected instruction still lacks a project outcome, owner, or completion boundary.
11. Continue only through the approved attended routing and execution workflow.

## Required user-visible structure

A question should state the stable meaning, identify the narrow uncertainty, and provide the leading interpretation when justified. Example:

> I understand that you want to build Phase 1, and LEW may be the application name. Did you mean: “Build Phase 1 of LEW”?

## Replay recovery

- Identical resolution identity: return `duplicate_ignored`; do not reclassify or write providers again.
- Different resolution for the same analysis: fail closed with a replay conflict.
- Answer bound to another capture or correlation ID: reject.
- Missing original capture or analysis digest: do not resume.

## Partial-failure recovery

If analysis succeeds but the item status cannot be recorded, do not claim the item is paused. Read back the authoritative item before continuing.

If the question is shown but the answer cannot be persisted, preserve the answer in the attended operation and retry only the exact evidence write after readback. Do not create downstream records until the resolution is bound.

If re-analysis succeeds but routing fails, retain the resolution and re-analysis digest. Resume at routing; do not ask the same question again.

## Rollback

Restoring the immediate authorized rollback removes v8.1.0 clarification behavior and returns to predecessor clarification handling. No production schema reversal is required because v8.1.0 introduces no Notion migration. Original captures and existing records remain unchanged.

## Prohibited recovery shortcuts

Do not silently normalize text, infer provider authorization, create a placeholder Todoist task, rewrite the original capture, bind an answer by title alone, use Google Drive as authority, or persist a transaction-specific answer as general user intent memory.
