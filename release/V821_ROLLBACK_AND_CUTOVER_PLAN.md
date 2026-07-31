# Atlas ROS v8.2.1 Rollback and Cutover Plan

The v8.2.1 cutover is staged: create and validate the new ledger; baseline it under
an exact attended authorization; then publish and activate only the exact retained
package. Existing reconciliation remains disabled until a verified checkpoint exists.

Rollback never restores W04. Preserve the new database, every baseline evidence row,
and the verified checkpoint. If the active or immediate rollback package cannot safely
consume the new shared ledger, stop activation and retain the current authority. For a
partial baseline, preserve verified rows, do not create the checkpoint, correct the
cause, and resume the same exact plan only after a fresh exact authorization.
