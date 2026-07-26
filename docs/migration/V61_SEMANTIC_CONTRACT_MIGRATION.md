# Atlas ROS v6.1 Semantic Contract Migration

## Compatibility strategy

v6.1 adds new contracts rather than changing v6 meanings in place. V3 reasoning and V2 management/execution contracts remain available for rollback and compatibility consumers.

## Safe projections

- `ReasoningPackageV4.project_v3()` is allowed only after intent is resolved and writes the primary business outcome into the legacy desired-outcome field.
- `ManagementPackageV3.project_v2()` is allowed only when structurally complete and includes only current business actions in legacy execution-candidate metadata.
- V3 semantic execution plans stop before the existing orchestration boundary; adapters cannot create additional work.

## Planning-model migration

- Controlled pilots use `controlled-technology-pilot@3.0.0`.
- Explicit single outcomes use `single-business-outcome@3.0.0`.
- `team-operating-model@2.0.0` remains compatible with Reasoning V3 and now declares V4/V3-management compatibility without changing its V2 behavior.

## Release behavior

v6.0.0 remains Active throughout development. No current Notion or Todoist objects are automatically rewritten. Historical benchmark records remain immutable. After explicit v6.1 promotion, v6.0.0 becomes the immediate rollback.
