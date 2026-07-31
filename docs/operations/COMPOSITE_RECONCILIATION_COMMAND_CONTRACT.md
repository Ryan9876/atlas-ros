# Composite ROS Reconciliation Command Contract

Status: v8.2.0 candidate contract; inactive until exact-package promotion.

## Invocation mapping

| Invocation | Scope |
|---|---|
| `Reconcile ROS` | Universal Inbox plus mapped Todoist parents, subtasks, comments, execution changes, and unprocessed ledger events |
| `Reconcile ROS inbox` | Same composite ingress scope |
| `Reconcile Universal Inbox only` | Universal Inbox only |
| `Reconcile Todoist only` | Mapped Todoist execution objects, comments, changes, and unprocessed ledger events |
| `Reconcile <task name or task ID>` | One uniquely resolved mapped Todoist parent and linked children |

## Required report

Every dry run reports the exact sources selected; Inbox, parent, subtask, and comment counts; new event IDs; explicit commands; natural actionable transitions; informational, blocked, and ignored events; exact proposed Notion and Todoist operations; explicit versus inferred fields; confidence, blockers, required authorization, and replay identity.

An unseen blocked or ignored event must be reported even when proposed provider mutations are zero.

## Stages

1. Resolve live authority and integration state.
2. Retrieve canonical source objects.
3. Build stable event identities.
4. Interpret explicit commands or bounded deterministic natural language.
5. Produce a typed review plan.
6. Bind attended authorization to the exact plan digest and actionable event IDs.
7. Execute only authorized operations.
8. Read back every write.
9. Record every event outcome.
10. Replay and verify zero duplicate effects.

Composite ingress does not merge source authority. Universal Inbox routing and Todoist execution reconciliation retain their own owned fields and write handlers.
