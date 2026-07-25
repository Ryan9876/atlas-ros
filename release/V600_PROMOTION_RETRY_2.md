# Atlas ROS v6.0.0 Promotion Retry 2

Final release asset publication and checksum readback passed in run `30144800134`; the remaining
failure was isolated to the restoration and benchmark phase. Production authority remained Atlas
ROS v5.6.0.

The controller was revised in commit `4ba1fecc755d07ef4e90051b56f7a07b2319f8f0` to install the
checksum-verified final wheel, extract the checksum-verified source distribution for evaluation,
and run planning, orchestration, reconciliation, W-retirement, rollback, and tag-target checks as
separate fail-closed gates.

This retry remains bound to exact candidate `3961d4880b3ed7542314d91b79c6b4780c0952f1`, package
SHA-256 `147aa08e3d60e17cf6b3f25099b3d00080e954b0a78cf7971bc08c58fa78bf63`, Full
Validation `V4V-34`, promotion decision `V4D-29`, and immutable rollback Atlas ROS v5.6.0.
