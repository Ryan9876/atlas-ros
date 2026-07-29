# v7.3 Requirement-to-Implementation Traceability

| Requirement | Implementation | Validation |
|---|---|---|
| Immutable evidence and snapshot | `contracts/operational_awareness`, `snapshot.py` | contract replay and deterministic snapshot tests |
| Work-state intelligence | `work_state/engine.py` | child/parent, approval, contradiction tests |
| Commitment intelligence | `commitments/engine.py` | acceptance and ambiguity tests |
| Exception brief | `operating_brief/engine.py` | ranking, deduplication, 10-item budget tests |
| Context and resumption | `execution_context/engine.py` | known/unknown resumption tests |
| Work graph hygiene | `work_graph_hygiene/engine.py` | duplicate, orphan, protected repair tests |
| Explicit lifecycle commands | `command_lifecycle/parser.py`, `planner.py` | ambiguity, replay, parent preservation tests |
| Canonical planning | `planning/operational_awareness.py` | exact operation and budget tests |
| Coordinators | `application/operational_awareness.py`, `command_lifecycle.py` | zero-write receipt tests |
| Read adapters | Notion/Todoist operational adapters | adapter boundary and fixture tests |
| Policy | `operational-awareness.yaml` + schema/compiler | digest and schema validation |
| CLI | `entry_points/awareness.py`, `lifecycle.py` | smoke tests |
| Notion migration | `release/v730-notion-schema-migration.yaml` | dry-run validator; unapplied |
| Actions optimization | v7.3 lean/full workflows | path, concurrency, build-once checks |
