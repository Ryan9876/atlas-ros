# Composite ROS Reconciliation Command Contract

## Candidate invocation mapping

| Invocation | Scope |
|---|---|
| `Reconcile ROS` | Universal Inbox plus mapped Todoist parents, subtasks, comments, execution changes, and unprocessed ledger events |
| `Reconcile ROS inbox` | Same composite ingress scope |
| `Reconcile Universal Inbox only` | Universal Inbox only |
| `Reconcile Todoist only` | All mapped Todoist execution objects and comments |
| `Reconcile <task name or task ID>` | One resolved mapped Todoist parent |

## Stages

1. Read live authority and integration state.
2. Retrieve authoritative source objects.
3. Build stable source-event identities.
4. Interpret explicit commands or deterministic natural language.
5. Present inferred values, provenance, blockers, conflicts, and exact operations.
6. Bind attended authorization to the exact plan digest and event IDs.
7. Execute only authorized provider operations.
8. Read back every write.
9. Record event outcomes.
10. Replay the same scope and verify zero duplicates.

Composite planning does not merge source authority. Universal Inbox routing and Todoist execution reconciliation retain their own records, rules, and write handlers.
