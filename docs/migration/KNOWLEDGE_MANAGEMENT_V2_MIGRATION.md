# Knowledge and Management V2 Migration

Existing callers may continue using `compose()` and `structure()` with V1 contracts. New callers
select a planning model in `ReasoningPackageV3`, call `compose_v2()`, validate the returned digest,
then call `structure_v2()`. Callers must not infer completeness from section presence; read
`lifecycle_status`, `section_completeness`, `decision_points`, and validation results.

To add a model, place the authoring YAML under `config/planning-models/`, copy the exact file into
`src/atlas_ros/data/planning-models/`, register compatible modules, and extend benchmark fixtures.
The same checksum-equivalence gate applies to knowledge modules. Never replace an existing
version in place: add a semantic version and mark superseded definitions deprecated with a
replacement reference. Retired versions do not resolve.

Rollback is code-only: restore Atlas ROS v5.3.0. This candidate performs no provider writes and
does not migrate external data, so no reverse data migration is required.
