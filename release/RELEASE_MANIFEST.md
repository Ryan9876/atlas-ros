# Atlas ROS v5.6.0 Release Manifest

Status: Active production release after successful exact-candidate validation, checksum-bound GitHub staging and authoritative readback, Drive-independent restoration proof, Full Validation Review V4V-32, and Ryan Smith's explicit production-promotion authorization on 2026-07-24.

- Package version: `5.6.0`
- Validated candidate head: `d1ccbcee318440fe6a4ac9fdf012ca4268b4389d`
- Production merge commit: `96d22de7d1a53aa8ca35750f6930048fafff8534`
- Final identity commit: `edc92d98fa306cd7a7f0e3e49d0a39ebdd6111bb`
- Standard CI run: `30138801848`
- Pull-request release-candidate run: `30138801843`
- Release-branch validation run: `30138862211`
- Validated candidate artifact ID: `8613773635`
- Validated artifact ZIP SHA-256: `56385c26e5b9ba171c2a4d125be62a005806dd1a5e87e498555dbdfae82ec258`
- Validated candidate package SHA-256: `6a01b0aef23e93da65c340722d5cc7f390a31a49a61526294988b26e1af97b71`
- Draft staging and restoration run: `30138862209` — passed
- Governed review: `V4V-32 — Atlas ROS v5.6.0rc1 Full Validation` — Passed; no blocking findings
- Promotion decision: `V4D-28 — Designate exact Atlas ROS v5.6.0 candidate promotion-ready`
- Promotion authorized: Yes — Ryan Smith, 2026-07-24
- Previous Active authority and immediate immutable rollback: Atlas ROS v5.5.0

## Authority model

GitHub is the canonical source, architecture, policy, schema, runbook, release, validation,
restoration, and historical-software authority. Notion remains the live dynamic management
authority. Todoist remains the attended execution authority. The fixed Google Drive Release Index
remains the initialization bootstrap, while historical Drive release folders remain allowlisted
legacy-read-only records.

Required production integrations remain Google Drive, Notion, and Todoist. Integration Inventory
authority: https://app.notion.com/p/8ba4fafb5ce244ef9add3013aff3746b

## Release scope

This release completes roadmap Wave 5 Execution Orchestration and Provider Separation: immutable
authorization, command, provider-operation, transaction, journal, recovery, and receipt contracts;
exact scoped attended authorization; deterministic provider-neutral command construction; bounded
retries; idempotent replay; uncertain-apply readback; partial-failure and compensation handling;
fail-closed receipts; content-safe evidence; Todoist and Notion execution adapters; W03
compatibility; provider-separation architecture gates; versioned schemas; and release-blocking
orchestration benchmarks.

Planning remains provider-neutral and cannot authorize or write. Adapters cannot plan, authorize,
or produce receipts. The orchestrator cannot add execution steps or reinterpret planning intent.
Existing V1 contracts, W-number interfaces, and legacy entry points remain available. Calendar,
messaging, email, deletion, autonomous scheduling, and unattended consequential automation remain
inactive unless separately authorized.

## Validation

Ruff, architecture validation, strict MyPy, 408 tests, 88.27% branch coverage, 52/52 Execution
Planning benchmark cases, 64/64 Execution Orchestration benchmark cases, 54/54 critical fixtures,
zero unauthorized provider writes, zero live writes, deterministic dependency policy, PyPI and OSV
advisory audits with no known vulnerabilities, source and wheel builds, clean-wheel installation,
canonical and extracted-source verification, SBOM/package consistency, all 33 publication
checksums, checksum-bound draft upload/readback, Drive-independent restoration, Decision Log
readback, Review Record readback, Automation Register validation, Integration Inventory validation,
and rollback-integrity confirmation passed.

The readable published workspace is valid when this manifest, validation evidence, planning and
orchestration benchmarks, architecture evidence, dependency-security evidence, SBOM, canonical
checksums, source distribution, wheel, candidate package, final release assets, production source
commit, and rollback record are readable, internally consistent, checksum-valid, and successfully
read back from their authoritative GitHub and Notion locations. Secrets and private signing
material are excluded.
