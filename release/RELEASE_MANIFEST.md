# Atlas ROS v6.2.0 Release Manifest

Status: Active production release after exact-candidate validation, Exact-Artifact Full Validation V4V-44, Ryan's explicit promotion authorization V4D-35, governed final-publication controller validation V4V-45, final GitHub publication, immutable tag verification, published-asset restoration, and post-publication readback on 2026-07-27.

- Package version: `6.2.0`
- Validated candidate head: `6e18b270d125c297309915fb8cde545bc65ee5e1`
- Candidate merge commit: `bc927a7d8c149d81e3372a3e6abfc220f557de6d`
- Publication-controller validated head: `d70121592a77f6d8c828d325319f486cd7e3b5cc`
- Publication-controller merge commit, production source, and final tag target: `863d5ddf9ebd4723200166cf31c7acd93ebec54f`
- Candidate standard CI run: `30227841581` — passed
- Candidate release-validation run: `30227841583` — passed
- Validated candidate artifact ID: `8639092941`
- Validated candidate artifact digest: `3fce62663cf2897ed9149d3c3dca07d698f6324ba0b25a25f12388e3ce8f2f60`
- Validated candidate wheel SHA-256: `c0d578e4abbc461c58250cf0eb8a611be2b6c6ac9679443fae2e1e47a104c24a`
- Final-controller standard CI run: `30228860476` — passed
- Final-publication controller validation run: `30228860474` — passed
- Final-publication validation artifact ID: `8639427126`
- Final-publication validation artifact digest: `eca56eec92efa9b05136ddb137fdbfcc7488d866318ed2b588b8974e42219ef1`
- Final wheel SHA-256: `83b8f468a05dbbbf1405e438a1b7bf02e202e6da2c369b6ca389175c7f4cb381`
- Final source SHA-256: `09ca00420e6c82982aff7b2964dabc97808e8afd9a58c297c3bddc6809952122`
- Post-publication verification head: `1d65ea53bbb88bb1fa5a072d222bc71eb2b580b2`
- Post-publication verification run: `30229506831` — passed
- Post-publication verification artifact ID: `8639608992`
- Post-publication verification artifact digest: `46bd8ddeebe019d43c9d1127d80c8f16eaa58e3bd754753e89a9678377461a58`
- Published at: `2026-07-27T01:08:43Z`
- Governed reviews: `V4V-44 — Atlas ROS v6.2.0rc1 Exact-Artifact Full Validation` and `V4V-45 — Atlas ROS v6.2.0 Final Publication Controller Validation` — Passed with Findings; no blocking findings
- Promotion decision: `V4D-35 — Promote exact Atlas ROS v6.2.0 candidate to Active production`
- Final release: `https://github.com/Ryan9876/atlas-ros/releases/tag/v6.2.0`
- Immediate immutable rollback: Atlas ROS v6.1.1 at production source `e1b842765376c9e36bbdee981cddead3feb97173`
- Historical rollback retained: Atlas ROS v6.1.0 at production source `15a62f670d250ec3728242f776d08449a9a95d1c`
- Provider writes during validation and publication verification: `0`

## Authority model

GitHub is the canonical source, architecture, policy, schema, runbook, release, validation, restoration, and historical-software authority. Notion remains the live dynamic management authority. Todoist remains the attended execution authority. The fixed Google Drive Release Index remains the initialization bootstrap, while historical Drive release folders remain immutable legacy-read-only records.

Required production integrations remain Google Drive, Notion, and Todoist. Integration Inventory authority: https://app.notion.com/p/8ba4fafb5ce244ef9add3013aff3746b

## Release scope

Atlas ROS v6.2.0 implements the governed fourteen-capability adaptive input-processing architecture:

1. multidimensional intent confidence;
2. typed intent graphs;
3. explicit dependency discovery;
4. governed planning archetypes;
5. business-intent and domain-knowledge separation;
6. typed constraint propagation;
7. canonical intent compression;
8. high-value clarification selection;
9. presentation-only planning-style recognition;
10. structured reflection and quality gating;
11. dynamic inherent and residual risk;
12. multi-outcome recognition;
13. governed planning-memory consultation; and
14. adaptive minimum-path projection.

The release preserves the exact v6.1.1 CloudVision parent and three management checkpoints, provider-free reasoning, attended execution, authorization boundaries, provider separation, canonical reconciliation, rollback, historical immutability, and fail-closed behavior.

No Todoist, calendar, email, messaging, deletion, live network execution, autonomous scheduling, provider-write, or integration-scope authority was added.

## Validation

Ruff, architecture validation, strict MyPy, dependency and secret security, 480 tests with 88.7854% branch-aware coverage, Classification Intelligence, Knowledge Management, Semantic Fidelity, Reasoning Coherence, Execution Planning, Execution Orchestration, Canonical Reconciliation, Adaptive Input Processing, CloudVision control-variant invariance, source and wheel construction, clean installation, exact source restoration, v6.1.1 immediate rollback restoration, v6.1.0 historical rollback restoration, SBOM identity, source and publication checksums, and zero-provider-write controls passed.

The published release was independently read back after publication. All ten required release assets were present; published checksums passed; final source and wheel hashes matched `FINAL_IDENTITY.json`; the immutable `v6.2.0` tag pointed exactly to `863d5ddf9ebd4723200166cf31c7acd93ebec54f`; the published wheel installed cleanly; the CloudVision regression contract passed; and the readable published workspace was valid.

Final publication performance measured v6.2 p95 at `2.384021 ms` versus v6.1.1 p95 at `3.160364 ms`, a `24.56%` improvement.

## Non-blocking historical finding

The immutable v6.1.0 distribution metadata reports `6.1.0`, while its internal `atlas_ros.__version__` reports `5.0.0rc1`. The package remains installable and was restored successfully. Historical assets remain unchanged.

## Published workspace validity

The readable published workspace is valid: the active manifest, release notes, scope, final identity, benchmark evidence, rollback evidence, SBOM, checksums, source distribution, wheel, final GitHub Release, production source, immutable final tag, and v6.1.1 immediate rollback record are readable and internally consistent. Secrets and private signing material are excluded.
