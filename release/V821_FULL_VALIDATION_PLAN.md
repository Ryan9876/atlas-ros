# Atlas ROS v8.2.1 Full Validation Plan

## Candidate scope

v8.2.1 remediates the v8.2.0 reconciliation-state configuration that targeted a
deleted historical W04 ledger. Candidate preparation creates no production
provider records and does not publish or activate a release.

## Required gates

1. Ruff and strict MyPy for the ledger, baseline, CLI, adapters, and reconciliation service.
2. Full test suite, coverage threshold, architecture and legacy-isolation checks.
3. Ledger validation coverage for deleted, historical, invalid, non-unique, missing,
   and cross-surface targets; SQLite fallback must fail in production mode.
4. Baseline coverage for mapped parent and subtask comments, deterministic digests,
   aliases, post-cutover exclusion, exact authorization, readback, partial failure,
   conflict, checkpoint gate, and zero-write replay.
5. Secret scan, dependency audits, build-once source/wheel, and clean-install readback.
6. Restore the live Active release and immediate rollback resolved from live authority.
7. Verify that W04 stays deleted and that no validation action writes Notion or Todoist.

## Production-gated evidence

The new database/data-source identifiers, baseline source inventory, baseline event
inventory, checkpoint, and final cross-authority readback do not exist during
Phase A. They must be created only after separately authorized production steps and
then bound into the final immutable release package.
