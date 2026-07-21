# Atlas ROS v4.5.0 Release Manifest

Status: Active production release upon publication and authority-record readback.

Base authority: Atlas ROS v4.4.2. Immediate immutable rollback: Atlas ROS v4.4.2.

This release formalizes execution-state management across Todoist and Notion. The Todoist Work project uses five unambiguous governed sections: Leadership & Team, Active Projects, Operations, Waiting on Others, and Development & Learning. Waiting on Others is a temporary dependency state, not a permanent work category.

Execution Steps now support optional Execution Priority and explicit Execution State. Blank step priority inherits the parent Action Record priority; explicit P1-P4 values override it. W04 reconciles Todoist subtask priority, due date, completion, labels, section state, and governed @atlas commands.

The production Risks and Blockers database is the governed destination for @atlas risk:, blocker:, dependency:, and issue: commands. Records use Todoist comment IDs as idempotency keys and may link to both the parent Action and applicable Execution Step.

Integration Inventory authority: https://app.notion.com/p/8ba4fafb5ce244ef9add3013aff3746b
Required production integrations remain Google Drive, Notion, and Todoist. Each must remain production, connected, approved, accepted, current, and least-privilege verified.

The readable published workspace is valid. The package contains this manifest and CHECKSUMS.sha256; restored-source verification must succeed before use. Secrets are excluded.

Shared reconciliation state data source: afbb753c-3112-4784-9165-f786b503d1f7.
Action Records data source: 8801f021-2b5d-494e-bc04-cdaf32067eb4.
Execution Steps data source: 190d7b89-c534-4638-a8a8-42df967a5afe.
Delegated Work data source: 6d035d30-6c3b-4e69-b67d-2f0315831eb3.
Risks and Blockers data source: 3f873502-8717-4ab2-9080-df07b7c4aeae.

This release does not activate autonomous scheduling, messaging, email, calendar actions, deletion, or unattended consequential automation.

Promotion authority: Ryan Smith, 2026-07-21.
