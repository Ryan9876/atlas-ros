# Atlas ROS v4.5.2 Release Manifest

Status: Validated production candidate. Promotion requires successful authority-record readback.

Base authority: Atlas ROS v4.5.1. Immediate immutable rollback upon promotion: Atlas ROS v4.5.1.

Release class: Material executable hardening and contract remediation.

This release supplies the executable implementation and packaged policy configuration for the Atlas ROS v4.5 operating model. It enforces the Todoist `**Objective:**` and `**Done when:**` content contract, creates and verifies ordered parent/subtask trees, makes W04 command processing retry-safe, uses snapshot-consistent checkpoints, implements risk/dependency/issue reconciliation, strengthens adapter and release security, and adds migration, durability, and regression coverage.

Required production integrations remain Google Drive, Notion, and Todoist. Integration Inventory authority: https://app.notion.com/p/8ba4fafb5ce244ef9add3013aff3746b

Validation gates: Ruff, strict MyPy, 58 tests, branch coverage above the 85% threshold, source and wheel builds, clean-wheel installation, packaged-policy smoke test, deterministic dependency-lock validation, vulnerability-exception validation, current advisory-policy enforcement in GitHub Actions, checksum verification, and full release review.

The readable published workspace is valid when this manifest, the validation report, dependency-security evidence, SBOM, checksums, source distribution, and wheel are readable and post-write readback succeeds. Secrets and private signing material are excluded.

This release does not activate autonomous scheduling, messaging, email, calendar actions, deletion, or unattended consequential automation.

Promotion authority: Ryan Smith, 2026-07-21.
