# Atlas ROS v5.1 Release Scope

Status: Candidate implementation pending validation and governed promotion.

## Included changes

- ROS Capture optional assertions for due date, delegation, and additional context.
- Capture remains routed through W01 and the Universal Inbox boundary.
- Todoist-originated state changes remain routed through W04 reconciliation.
- W03 Todoist section routing by management domain with deterministic precedence and explainability.
- Todoist Done when formatting enforcement at the write boundary.
- Parent-subtask hierarchy preservation and readback validation during section moves.

## Excluded changes

- Autonomous scheduling, messaging, email, calendar actions, deletion, or unattended consequential automation.
- Direct Capture-to-Todoist or Capture-to-final-Notion writes.
- The proposed modular cognitive-engine redesign in IDEA-4; that remains a separate architectural program requiring its own implementation and migration plan.

## Rollback

Atlas ROS v5.0 remains unchanged and is the immediate rollback for this candidate until a later promotion decision changes authority.
