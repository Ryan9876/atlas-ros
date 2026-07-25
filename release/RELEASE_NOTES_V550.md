# Atlas ROS v5.5.0rc1 Release Notes

This release candidate completes Execution Planning and Task Economy. Management Package V2 now
flows through deterministic candidate extraction, a structured 14-condition Task Projection
Test, layered duplicate and existing-representation analysis, progressive horizons, governed
task budgets, and a digest-bound provider-independent Execution Plan V2.

The default plan remains one parent with zero to three meaningful subtasks. Four or five require
explicit evidence that every step is distinct, current, ready, independently executable, and
valuable. More than five produces a decomposition-review requirement and no automatic subtasks.
When genuinely independent parent outcomes are present, the planner emits separate proposals only
after each parent passes the full test and its children explicitly identify that parent.
Knowledge Modules, management sections, governance, evidence, uncertainty, risk, and future
phases do not inflate task count unless an item independently passes the full projection test.

Existing V1 APIs and the W03A facade remain supported. Unsafe lossy V2 projections fail closed.
The planner cannot authorize, call providers, write Todoist objects, or emit receipts. Rollback is
Atlas ROS v5.4.0; no external data migration is performed.
