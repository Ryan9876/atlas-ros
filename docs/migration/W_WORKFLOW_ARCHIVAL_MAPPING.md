# W-Workflow Archival Mapping

Status: Development cutover record. Production remains Atlas ROS v5.1.1 until separately promoted.

| Legacy entrypoint | Canonical capability | Compatibility status |
|---|---|---|
| W01 capture | Capture Service | Alias retained |
| W02 routing | Management Reasoning Engine + Record Routing Service | Alias retained |
| W03A decomposition | Execution Planner | Alias retained |
| W03 Todoist | Execution Orchestrator + Todoist Execution Adapter | Alias retained |
| W04 reconciliation | Execution Reconciliation Service | Alias retained |

## Cutover rules

1. New internal development code imports from `atlas_ros.capabilities` or the named semantic packages.
2. Direct W-module imports are limited to compatibility adapters, archival tests, and the semantic export boundary.
3. W aliases remain behavior-preserving and receive regression coverage until a separately authorized major removal release.
4. Production activation, alias deletion, and authority migration are not implied by this development cutover.
5. Rollback remains the current immutable Atlas ROS v5.1 package until a later promotion changes release authority.
