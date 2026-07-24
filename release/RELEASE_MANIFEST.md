# Atlas ROS v5.4.0 Release Manifest

Status: Active production release after successful exact-candidate validation, checksum-bound GitHub staging and authoritative readback, Drive-independent restoration proof, Full Validation Review V4V-30, and Ryan Smith's explicit production-promotion authorization on 2026-07-24.

- Package version: `5.4.0`
- Validated candidate head: `514577b8718e813800eac91cc3f93b193c04b07b`
- Production merge commit: `da93863dd7990ed17a1be04fadfed2ad1c33a70e`
- Final identity commit: `f4f68db5aecef97a51790a7205e99e9e35826b17`
- Standard CI run: `30128391863`
- Release-candidate workflow run: `30128391868`
- Validated candidate artifact ID: `8610149494`
- Validated candidate package SHA-256: `e6339e214d40af42e371b7ca71931e713d0a0b4775b562fad4eba3842d489ca6`
- Draft staging and restoration: `v5.4.0-rc.1` — passed
- Governed review: `Atlas ROS v5.4.0rc1 Knowledge Composition and Management Structure Full Validation` — Passed; no blocking findings
- Promotion decision: `V4D-26 — Promote Atlas ROS v5.4.0 to Active production`
- Promotion authorized: Yes — Ryan Smith, 2026-07-24
- Previous Active authority and immediate immutable rollback: Atlas ROS v5.3.0

## Authority model

GitHub is the canonical source, architecture, policy, schema, runbook, release, validation, restoration, and historical-software authority. Notion remains the live dynamic management authority. Todoist remains the attended execution authority. The fixed Google Drive Release Index remains the initialization bootstrap, while historical Drive release folders remain allowlisted legacy-read-only records.

Required production integrations remain Google Drive, Notion, and Todoist. Integration Inventory authority: https://app.notion.com/p/8ba4fafb5ce244ef9add3013aff3746b

## Release scope

This release completes roadmap Wave 3 Knowledge Composition and Management Structure: versioned Planning Model and Knowledge Module registries, deterministic dependency resolution, explicit Planning Model selection in Reasoning Package V3, Knowledge Package V2, Management Package V2, a complete 14-section Team Operating Model, provenance, completeness, governance, schemas, evaluation, migration guidance, and restoration evidence.

The release remains non-executing at the Knowledge and Management package boundary. It does not call provider adapters, create Todoist tasks, change integration permissions, alter autonomous schedules, or retire W-number interfaces. Existing V1 contracts and legacy entry points remain available, with fail-closed V2 projections when a lossy conversion would be unsafe. Calendar, messaging, email, deletion, autonomous scheduling, and unattended consequential automation remain inactive unless separately authorized.

## Validation

Ruff, architecture validation, strict MyPy, 340 tests, 88.63% branch coverage, deterministic dependency policy, PyPI and OSV advisory audits with no known vulnerabilities, two Knowledge and Management benchmark cases, source and wheel builds, clean-wheel installation, canonical and extracted-source verification, SBOM/package consistency, six critical restoration-document validation, restoration-companion checksum verification, outer package checksum verification, 21/21 publication checksum verification, checksum-bound draft upload/readback, Drive-independent restoration, Decision Log readback, Review Record readback, Automation Register validation, Integration Inventory validation, and rollback-integrity confirmation passed.

The readable published workspace is valid when this manifest, validation evidence, dependency-security evidence, SBOM, canonical checksums, source distribution, wheel, candidate package, final release assets, production source commit, and rollback record are readable, internally consistent, checksum-valid, and successfully read back from their authoritative GitHub and Notion locations. Secrets and private signing material are excluded.
