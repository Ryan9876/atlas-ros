# Atlas ROS v8.2.0 Full Validation Plan

## Exact candidate binding

- Candidate version: 8.2.0
- Candidate commit: supplied by the workflow trigger and verified against `HEAD`
- Authority baseline: resolved from `origin/main` at run time
- Build count: exactly one

## Gates

1. Ruff across all changed source, tests, and release helpers.
2. Strict MyPy for the changed production modules.
3. Architecture, development-tool, legacy-isolation, schema-generation, documentation-authority, dependency-lock, and vulnerability-policy checks.
4. Full pytest suite with JUnit and coverage JSON; no skipped or failed tests.
5. Explicit v8.1 clarification regression suite.
6. Exact Todoist-comment connector fixture through dry-run planning, exact authorization, fake-provider readback, and zero-duplicate replay.
7. Scoped secret scan over all changed text files.
8. PyPI and OSV audits against the hash-locked runtime requirements.
9. Build-once source distribution and wheel.
10. Clean source and wheel installation with `status` and `verify` readbacks.
11. Active-release and immediate-rollback restoration from live authority.
12. No-production-schema validation and existing-ledger-schema evidence.
13. Provider dry-run receipt with Notion writes 0, Todoist writes 0, and total production provider writes 0.
14. SPDX SBOM, source-tree digest, package index, and evidence checksum generation.
15. Retained artifact upload for independent readback and promotion authorization.

## Promotion threshold

The candidate is authorization-ready only when every gate passes and the retained artifact identities are available. Preparation does not authorize publication or activation.
