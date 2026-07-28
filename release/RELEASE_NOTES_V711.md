# Atlas ROS v7.1.1 Release Notes Candidate

Atlas ROS v7.1.1 reduces Quick Initialization orchestration weight without changing the v7 authority model. The new consolidated operation always reads live GitHub authority, reuses only eligible immutable authority material, reads compact mutable Notion state live, and performs a single additional Todoist liveness probe.

The release adds a compact receipt with exact release and rollback identity, authority agreement, integration readiness, cache path, stage timings, warnings, blocked condition, and explicit zero provider-write and Google Drive-read counts.

Existing cold `initialize` and `initialize_full` behavior remains supported. Production activation, Notion projection activation, and publication require separate exact authorization.
