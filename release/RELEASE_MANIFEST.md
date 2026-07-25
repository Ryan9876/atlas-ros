# Atlas ROS v6.0.0 Release Manifest

Status: Active production release after successful exact-candidate validation, checksum-bound GitHub staging and authoritative readback, Drive-independent restoration proof, Full Validation Review V4V-34, and Ryan Smith's explicit production-promotion authorization V4D-29 on 2026-07-25.

- Package version: `6.0.0`
- Validated candidate head: `3961d4880b3ed7542314d91b79c6b4780c0952f1`
- Production merge commit: `fb56b8fad0104deef19d9c83eadd63a3f0d009be`
- Final identity commit: `791100d616a4f9732183b4f8fca06d7f40597992`
- Standard CI run: `30144362938`
- Pull-request release-candidate run: `30144362937`
- Release-branch validation run: `30144365830`
- Validated candidate artifact ID: `8615505710`
- Validated artifact ZIP SHA-256: `5427e1991887c56ccef441faeab9fa996e963567a00bacc3d67df9fee5daa73a`
- Validated candidate package SHA-256: `147aa08e3d60e17cf6b3f25099b3d00080e954b0a78cf7971bc08c58fa78bf63`
- Draft staging and restoration run: `30144365818` — passed
- Governed review: `V4V-34 — Atlas ROS v6.0.0rc1 Exact-Artifact Full Validation` — Passed; no blocking findings
- Promotion decision: `V4D-29 — Promote exact Atlas ROS v6.0.0 candidate to Active production`
- Promotion authorized: Yes — Ryan Smith, 2026-07-25
- Previous Active authority and immediate immutable rollback: Atlas ROS v5.6.0

## Authority model

GitHub is the canonical source, architecture, policy, schema, runbook, release, validation,
restoration, and historical-software authority. Notion remains the live dynamic management
authority. Todoist remains the attended execution authority. The fixed Google Drive Release Index
remains the initialization bootstrap, while historical Drive release folders remain allowlisted
legacy-read-only records.

Required production integrations remain Google Drive, Notion, and Todoist. Integration Inventory
authority: https://app.notion.com/p/8ba4fafb5ce244ef9add3013aff3746b

## Release scope

This release completes the approved Atlas ROS Development Program Roadmap with Canonical
Reconciliation and Semantic Cutover: Reconciliation V2 contracts and schemas; declarative field
authority; deterministic provider-neutral plans; structured conflicts; command and event
idempotency; integrity-protected checkpoints; exact-plan attended authorization; verified readback
and fail-closed receipts; bidirectional development-record reconciliation; semantic-only runtime
ownership; numbered-workflow runtime retirement; breaking-change and migration guidance;
differential validation; restored-artifact validation; and immutable v5.6 rollback rehearsal.

Planning remains side-effect free. Adapters cannot plan, authorize, decide field authority, or
advance checkpoints. Reconciliation cannot create unplanned execution work. Todoist and Notion
provider writes remain attended, explicitly scoped, idempotent, and verified by readback. Calendar,
messaging, email, deletion, autonomous scheduling, and unattended consequential automation remain
inactive unless separately authorized.

## Validation

Ruff, architecture validation, strict MyPy, 433 tests, 88.657% branch coverage, 52/52 Execution
Planning benchmark cases, 64/64 Execution Orchestration benchmark cases, 54/54 critical fixtures,
77/77 Canonical Reconciliation cases, zero unexplained v5.6 differential drift, zero unauthorized
provider writes, zero live writes, zero runtime W modules, zero blocking W references,
deterministic dependency policy, PyPI and OSV advisory audits with no known vulnerabilities, source
and wheel builds, clean-wheel installation, canonical and extracted-source verification,
SBOM/package consistency, all 54 publication checksums, checksum-bound draft upload/readback,
Drive-independent restoration, Decision Log readback, Review Record readback, Automation Register
validation, Integration Inventory validation, development-record reconciliation, and v5.6 rollback
integrity confirmation passed.

The readable published workspace is valid when this manifest, validation evidence, planning,
orchestration, and reconciliation benchmarks, architecture evidence, dependency-security evidence,
SBOM, canonical checksums, source distribution, wheel, candidate package, final release assets,
production source commit, and rollback record are readable, internally consistent, checksum-valid,
and successfully read back from their authoritative GitHub and Notion locations. Secrets and
private signing material are excluded.
