# Atlas ROS v6.1.0 Release Manifest

Status: Promotion authorized under V4D-31; final publication, restoration readback, and live authority switching remain fail-closed until the final release controller passes.

- Package version: `6.1.0`
- Validated candidate head: `7cfa5e20fc3f30abf02d1a428c4ca3632811c1d7`
- Production merge commit: `bbed48eb3d00427486a480cf27eea493af9e9538`
- Standard CI run: `30190241909`
- Release-candidate run: `30190241886`
- Validated candidate artifact ID: `8628317565`
- Validated artifact-wrapper digest: `7230c205958a452bd256435998ad8897779557a1b74504fb29eb79333fe727a0`
- Validated candidate package SHA-256: `9aa9e6fd0447879881bce5c91ce8decefe5e6685e6c9ddc3b9dc8d1809c02237`
- Draft staging and restoration run: `30191103157` — passed
- Draft staging receipt SHA-256: `8fc7d226338647a4ea877308f4145cf15c99e588df99c4dba078de3b5d3479be`
- Governed review: `V4V-38 — Atlas ROS v6.1.0rc1 Exact-Artifact Full Validation` — Passed; no blocking findings
- Promotion decision: `V4D-31 — Promote exact Atlas ROS v6.1.0 candidate to Active production`
- Promotion authorized: Yes — Ryan Smith, 2026-07-26
- Previous Active authority and immediate immutable rollback after promotion: Atlas ROS v6.0.0
- Final publication and restoration run: pending

## Authority model

GitHub is the canonical source, architecture, policy, schema, runbook, release, validation,
restoration, and historical-software authority. Notion remains the live dynamic management
authority. Todoist remains the attended execution authority. The fixed Google Drive Release Index
remains the initialization bootstrap, while historical Drive release folders remain immutable
legacy-read-only records.

Required production integrations remain Google Drive, Notion, and Todoist. Integration Inventory
authority: https://app.notion.com/p/8ba4fafb5ce244ef9add3013aff3746b

## Release scope

Atlas ROS v6.1.0 restores outcome-centered execution planning by separating the primary business
outcome and current Ryan-owned actions from delegated, conditional, evaluation, audit,
provider-control, and reference instructions. It adds Intent Partition V1, Reasoning Package V4,
Management Package V3, Execution Candidate/Decision/Plan V3, Semantic Fidelity Result V1,
controlled-technology-pilot and single-business-outcome planning models, and a release-blocking
Semantic Fidelity Gate with expert golden and metamorphic tests.

For the CloudVision benchmark, Todoist receives one parent—`Launch the Arista CloudVision
code-upgrade automation pilot`—and three current management checkpoints covering scope and success
measures, technical ownership and low-risk targets, and pre-checks/change controls/evidence/rollback.
Delegated technical execution, conditional evidence review, comparison controls, duplicate-test
evidence, journals, receipts, IDs, hashes, and readback evidence remain outside Todoist.

Existing v6 orchestration, reconciliation, provider separation, exact attended authorization,
idempotency, readback, rollback, and fail-closed behavior remain unchanged. Calendar, messaging,
email, deletion, autonomous scheduling, and unattended consequential automation remain inactive.

## Validation

Ruff, architecture validation, strict MyPy, 439 tests, 88.7151% branch coverage, 12/12 Semantic
Fidelity cases, 7/7 CloudVision metamorphic invariance variants, 52/52 Execution Planning cases,
64/64 Execution Orchestration cases, 54/54 critical orchestration fixtures, 77/77 Canonical
Reconciliation cases, zero unexplained v6.0 differential drift, zero unauthorized or live provider
writes, dependency and advisory audits, source and wheel builds, clean-wheel installation, schema
and registry consistency, six critical restoration documents, 16/16 restoration-companion
checksums, 75/75 canonical publication checksums, 1,532 source-manifest entries, checksum-bound
draft publication/readback, Drive-independent restoration, Decision Log readback, Review Record
readback, Automation Register validation, Integration Inventory validation, and v6.0 rollback
integrity confirmation passed.

The readable published workspace is valid only after the final release controller verifies the final
tag target, final assets, package checksums, restored wheel, restored semantic/planning/orchestration/
reconciliation benchmarks, v6.0 rollback, and final GitHub Release metadata. Secrets and private
signing material are excluded.
