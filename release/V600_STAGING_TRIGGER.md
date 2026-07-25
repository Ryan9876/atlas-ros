# Atlas ROS v6.0.0rc1 Governed Staging Trigger

This commit freezes the exact candidate tree for checksum-bound draft GitHub Release staging and readback.

- Candidate line: Atlas ROS v6.0.0rc1
- Base production authority: Atlas ROS v5.6.0
- Immediate rollback if promoted: Atlas ROS v5.6.0
- Authorization: Ryan explicitly authorized completion of the remaining governed release work on 2026-07-25.
- Boundary: staging, validation, merge, publication, authority updates, and post-promotion reconciliation must each pass their required readback gate. A failed gate leaves production authority unchanged.
