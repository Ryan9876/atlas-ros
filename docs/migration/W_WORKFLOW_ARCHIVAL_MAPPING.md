# HISTORICAL — NOT CURRENT AUTHORITY — W-Workflow Archival Mapping

Status: Historical migration record preserved for numbered-workflow retirement context. Current operating authority is Atlas ROS v6.2.0 and the capability-based architecture. This document must not be used as a current runtime or production-status source.

| Legacy entrypoint | Canonical capability | Compatibility status |
|---|---|---|
| W01 capture | Capture Service | Retired in v6.0.0 |
| W02 routing | Management Reasoning Engine + Record Routing Service | Retired in v6.0.0 |
| W03A decomposition | Execution Planner | Retired in v6.0.0 |
| W03 Todoist | Execution Orchestrator + Todoist Execution Adapter | Retired in v6.0.0 |
| W04 reconciliation | Execution Reconciliation Service | Retired in v6.0.0 |

## Historical cutover rules

1. New internal development code imports from semantic capability packages.
2. Direct W-module imports are limited to compatibility adapters, archival tests, and historical evidence.
3. Current production documentation must use capability names rather than numbered workflow aliases.
4. Historical source, release artifacts, archival mapping, and rollback instructions remain preserved.
5. Current production authority is determined only by the fixed Release Index, Notion System State, and active release manifest.
