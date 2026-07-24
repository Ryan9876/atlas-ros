# Atlas ROS v5.1.1 Release Manifest

Release class: Immutable release-manifest and published-workspace validity correction.

Base authority: Atlas ROS v5.1. Immediate immutable rollback upon promotion: Atlas ROS v5.1.

This patch corrects release-authority documentation without expanding executable scope. It replaces the stale embedded v4.5.3 source manifest with the correct v5.1.1 identity and requires the generated published manifest to state the readable published workspace validity contract explicitly. The v5.1 workflow, policy, schema, integration scope, operating boundaries, and attended execution model remain unchanged.

Required production integrations remain Google Drive, Notion, and Todoist. Integration Inventory authority: https://app.notion.com/p/8ba4fafb5ce244ef9add3013aff3746b

Validation gates: Ruff, strict MyPy, complete regression tests with branch coverage above the 85% threshold, source and wheel builds, clean-wheel installation, packaged-policy smoke testing, deterministic dependency-lock validation, vulnerability-exception validation, dual-service advisory-policy enforcement, canonical source-manifest generation and verification, extracted-source verification, SBOM and package-version consistency, six critical restoration-document validation, restoration-companion checksum verification, outer release-artifact checksums, Google Drive publication/readback, Decision Log and Review Record readback, and rollback-integrity confirmation.

The readable published workspace is valid when this manifest, the validation report, dependency-security evidence, SBOM, canonical checksums, source distribution, wheel, and combined package are readable, internally consistent, checksum-valid, and successfully read back from their authoritative published locations. Secrets and private signing material are excluded.

This release does not activate autonomous scheduling, messaging, email, calendar actions, deletion, or unattended consequential automation.

Production promotion requires a governed review bound to the exact commit and artifact digest, successful publication and readback, and Ryan Smith's explicit authorization.
