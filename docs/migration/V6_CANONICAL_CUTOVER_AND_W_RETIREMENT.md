# Atlas ROS v6 Canonical Cutover and Numbered-Workflow Retirement

Atlas ROS v6 replaces numbered runtime ownership with semantic capabilities.

| Historical interface | Canonical replacement | Behavioral note |
|---|---|---|
| W01 capture | `atlas_ros.capture.CaptureService` | Event workflow label is `capture`. |
| W02 routing | `atlas_ros.services.RoutingService` | Controlled legacy/shadow/attended/semantic modes remain data-compatible. |
| W03A decomposition | `atlas_ros.planning.DecompositionService` and `ExecutionPlanner` | Planning remains provider-free and unauthorized. |
| W03 execution | `atlas_ros.services.TodoistService`, `ExecutionOrchestratorV2`, provider adapters | Exact attended authorization and readback remain mandatory. |
| W04 reconciliation | `atlas_ros.reconciliation.CanonicalReconciliationService` | Adds versioned authority, conflict, checkpoint, authorization, and receipt contracts. |

## Cutover checklist

1. Replace numbered imports with the table’s semantic imports.
2. Replace numbered configuration labels with `capture`, `routing`, `execution`, or
   `reconciliation`.
3. Validate custom code with the v6 retired-import scanner.
4. Dry-run reconciliation and review conflicts.
5. Use an attended exact-plan authorization for consequential writes.
6. Preserve the v5.6 release and rollback report.

The v6 package contains no numbered workflow modules or legacy facade package. Historical source,
release artifacts, archival mapping, and rollback instructions remain immutable.
