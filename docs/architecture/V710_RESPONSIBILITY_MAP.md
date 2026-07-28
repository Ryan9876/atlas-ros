# Atlas ROS v7.1 Candidate Responsibility Map

| Component | Owns | Must not own |
|---|---|---|
| Contracts | Typed immutable identities, plans, authorization, results, receipts | Policy, orchestration, providers |
| Policy | Retention, release, integration, compatibility, and architecture rules | Provider writes or planning |
| Capabilities | Provider-free classification, planning, compilation, simulation | Authorization or adapters |
| Application | Canonical coordination and exact authorized sequencing | Rewriting plans or inventing intent |
| Runtime | Lightweight command dispatch, validated registries, optional read-only cache | Release tooling, migration logic, provider truth |
| Adapters | Exact provider operations and readback | Planning or authorization |
| Reconciliation | Verified state projection under field authority | New execution intent |
| Migration packages | Explicit supported historical-input conversion | Production runtime imports |
| Release tooling | Candidate compilation, validation, packaging, restoration evidence | Production runtime imports or authority activation without authorization |

## New ownership

- Drive dependency inventory and retirement simulation: `tools/release/drive_dependency_inventory.py`, `tools/release/drive_retirement.py`
- Historical cleanup contracts: `src/atlas_ros/contracts/history.py`
- Historical cleanup planning: `src/atlas_ros/capabilities/historical_cleanup/`
- Historical cleanup transaction model: `tools/release/historical_cleanup.py`
- Release specification and compilation receipts: `src/atlas_ros/contracts/release.py`
- Version-neutral compiler: `tools/release/release_compiler.py`
- Lazy runtime: `src/atlas_ros/runtime/lazy.py`
- Optional warm cache: `src/atlas_ros/runtime/warm.py`
