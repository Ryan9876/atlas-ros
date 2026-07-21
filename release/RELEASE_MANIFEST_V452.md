# Atlas ROS v4.5.2 Candidate Release Manifest

Status: Validated candidate; not promoted.
Base authority: Atlas ROS v4.5.1. Proposed rollback: Atlas ROS v4.5.1 authority records with v4.5.0 executable baseline.
Release class: Material hardening and executable contract remediation.

This candidate supplies the executable implementation missing from v4.5.1, packages policy configuration, enforces the Todoist Objective/Done-when contract, creates and verifies ordered task trees, makes W04 command processing retry-safe, uses snapshot-consistent checkpoints, implements risk/dependency/issue reconciliation, strengthens adapter and release security, and adds migration, durability, and regression coverage.

Validation gates: Ruff, strict MyPy, 58 tests, 86.30% branch coverage, source and wheel builds, clean-wheel installation, packaged-policy smoke test, checksum verification, and independent re-review.

No autonomous scheduling, messaging, email, calendar, deletion, or unattended consequential automation is activated.
