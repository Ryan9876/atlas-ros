# Atlas ROS v6.0 Rollback Rehearsal

Status: passed.

The exact rollback target is the immutable Atlas ROS v5.6.0 release at production source
`06c5a703dec72135171d5738e6e0f3573ed8499d`.

- Final v5.6 publication and Drive-independent restoration run `30140577467` passed.
- The preserved v5.6 source completed 408 tests at 88.27% branch coverage.
- Its 52-case planning and 64-case orchestration benchmarks remain the rollback acceptance gates.
- The v6 differential harness found zero unexplained planning, hierarchy, routing, task-count, or
  command-parsing drift.
- No live provider writes occurred.

Rollback means restoring the published v5.6 release and its production source as Active authority.
The v5.5 historical rollback remains preserved but is not the immediate rollback for a promoted
v6 release.
