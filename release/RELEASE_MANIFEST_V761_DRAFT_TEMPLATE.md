# Atlas ROS v7.6.1 Draft Immutable Release Manifest Template

Status: non-publishing template; exact candidate values are generated only after the frozen candidate workflow passes.

## Package

- Version: `7.6.1`
- Exact source commit: `<candidate-commit>`
- Retained artifact: `<artifact-id>`
- Retained artifact SHA-256: `<artifact-digest>`
- Source distribution SHA-256: `<source-digest>`
- Wheel SHA-256: `<wheel-digest>`
- SBOM SHA-256: `<sbom-digest>`
- Source-manifest SHA-256: `<source-manifest-digest>`
- Validation receipt SHA-256: `<receipt-digest>`
- Build count: `1`

## Predecessor and rollback

- Active predecessor: Atlas ROS v7.6.0 at `<live-authority-commit>`
- Proposed immediate rollback after activation: Atlas ROS v7.6.0 at `<live-authority-commit>`
- Preserved lineage: Atlas ROS v7.5.2 at `<live-authority-rollback-commit>`

## Feature and profile

- Software feature at release activation: `disabled`
- Production Ryan profile present in package: `false`
- Profile activation: separate exact governed transaction
- Dedicated profile-projection schema: `<proposal-result>`
- Safe fallback: v7.6.0 baseline with preserved v7.5 clarification behavior

## Boundaries

This template does not authorize merge, publication, tag creation or movement, canonical authority activation, production schema mutation, profile installation or enablement, provider writes, Todoist tasks, messages, calendar actions, schedules, credentials, integration changes, deletion, forgetting execution, or live-network action.
